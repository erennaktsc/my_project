from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import json as json_lib
import time
from datetime import datetime

from app.models import db, User, Document, Topic, Question, ProcessingJob, Feedback, Favorite, FlashcardReview
from app.background_processor import start_background_job
from app.forms import RegisterForm, LoginForm
from flask import send_from_directory


main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Yüklenmiş dosyaları (özellikle kırpılmış kaynak görüntüleri) sunar."""
    return send_from_directory(os.path.join(os.getcwd(), 'uploads'), filename)


# ═══ AUTH ROUTES ═══

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=''
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı! Şimdi giriş yapabilirsin.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('register.html', form=form)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f'Hoş geldin, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.index'))
        else:
            flash('Geçersiz e-posta veya şifre.', 'error')
    
    return render_template('login.html', form=form)


@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptın.', 'success')
    return redirect(url_for('main.login'))


# ═══ ANA UYGULAMA ROUTES ═══

@main.route('/')
@login_required
def index():
    documents = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc()).limit(10).all()
    return render_template('index.html', documents=documents)


@main.route('/upload', methods=['POST'])
@login_required
def upload():
    """Dosya yükler ve arka plan işi başlatır. İşleme sayfasına yönlendirir."""
    if 'file' not in request.files:
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('main.index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Dosya seçilmedi', 'error')
        return redirect(url_for('main.index'))
    
    if not allowed_file(file.filename):
        flash('Sadece PNG, JPG, JPEG ve PDF desteklenir', 'error')
        return redirect(url_for('main.index'))
    
    # Dosyayı kaydet
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_filename = f"{timestamp}_{filename}"
    temp_path = os.path.join('uploads', temp_filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(temp_path)
    
    # Bir job oluştur
    job_id = str(uuid.uuid4())
    job = ProcessingJob(
        id=job_id,
        user_id=current_user.id,
        file_path=temp_path,
        status='pending',
        current_step='Hazırlanıyor...',
        progress=0
    )
    db.session.add(job)
    db.session.commit()
    
    # Arka planda işi başlat
    app = current_app._get_current_object()
    
   # Kullanıcının seçtiği soru sayısı (3, 5 veya 10 — varsayılan 3)
    # Kullanıcının seçtiği soru sayısı (3, 5 veya 10 — varsayılan 3)
    try:
        num_questions = int(request.form.get('num_questions', 3))
        if num_questions not in (3, 5, 10):
            num_questions = 3
    except (ValueError, TypeError):
        num_questions = 3
    
    # Bloom Taksonomisi seviyeleri (opsiyonel)
    valid_bloom_levels = ['hatirlama', 'anlama', 'uygulama', 'analiz', 'degerlendirme', 'yaratma']
    bloom_levels = request.form.getlist('bloom_levels')
    bloom_levels = [b for b in bloom_levels if b in valid_bloom_levels]
    if not bloom_levels:
        bloom_levels = None  # Karışık (varsayılan)

    start_background_job(app, job_id, temp_path, current_user.id, 
                         num_questions=num_questions, 
                         bloom_levels=bloom_levels)
    
    # Kullanıcıyı işleme sayfasına yönlendir
    return redirect(url_for('main.processing', job_id=job_id))


@main.route('/processing/<job_id>')
@login_required
def processing(job_id):
    """İşleme sayfasını gösterir (SSE ile canlı güncellenir)."""
    job = ProcessingJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        flash('Bu işleme erişim izniniz yok.', 'error')
        return redirect(url_for('main.index'))
    return render_template('processing.html', job=job)


@main.route('/job-stream/<job_id>')
@login_required
def job_stream(job_id):
    """SSE — Job durumunu canlı stream eder."""
    job = ProcessingJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        return Response('Unauthorized', status=403)
    
    app = current_app._get_current_object()
    
    def event_stream():
        last_status = None
        last_progress = -1
        max_wait = 120  # max 2 dakika
        start = time.time()
        
        while time.time() - start < max_wait:
            with app.app_context():
                current_job = ProcessingJob.query.get(job_id)
                if not current_job:
                    break
                
                # Değişiklik var mı?
                if (current_job.status != last_status or 
                    current_job.progress != last_progress):
                    
                    data = {
                        'status': current_job.status,
                        'current_step': current_job.current_step,
                        'progress': current_job.progress,
                        'detected_topic': current_job.detected_topic,
                        'detected_subtopics': current_job.detected_subtopics,
                        'detected_level': current_job.detected_level,
                        'content_type': current_job.content_type,
                        'document_id': current_job.document_id,
                        'error_message': current_job.error_message
                    }
                    yield f"data: {json_lib.dumps(data, ensure_ascii=False)}\n\n"
                    
                    last_status = current_job.status
                    last_progress = current_job.progress
                
                # Bittiyse veya hata olduysa dur
                if current_job.status in ('completed', 'failed'):
                    break
            
            time.sleep(1)  # her saniye kontrol et
    
    return Response(event_stream(), mimetype='text/event-stream')


@main.route('/document/<int:doc_id>')
@login_required
def view_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    if document.user_id != current_user.id:
        flash('Bu dokümana erişim izniniz yok.', 'error')
        return redirect(url_for('main.index'))
    
    topics = Topic.query.filter_by(document_id=doc_id).all()
    topic_data = []
    for topic in topics:
        questions = Question.query.filter_by(topic_id=topic.id).all()
        topic_data.append({
            'topic': topic,
            'questions': questions
        })
    
    return render_template('document.html', document=document, topic_data=topic_data)

@main.route('/document/<int:doc_id>/export-pdf')
@login_required
def export_document_pdf(doc_id):
    """Bir dökümanın sorularını PDF olarak dışa aktarır."""
    from flask import send_file
    from app.pdf_exporter import generate_questions_pdf
    
    document = Document.query.get_or_404(doc_id)
    
    if document.user_id != current_user.id:
        flash('Bu dokümana erişim izniniz yok.', 'error')
        return redirect(url_for('main.index'))
    
    # Konuları ve soruları topla
    topics = Topic.query.filter_by(document_id=doc_id).all()
    topic_data = []
    for topic in topics:
        questions = Question.query.filter_by(topic_id=topic.id).all()
        topic_data.append({
            'topic': topic,
            'questions': questions
        })
    
    if not any(item['questions'] for item in topic_data):
        flash('Bu döküman için henüz soru üretilmemiş.', 'error')
        return redirect(url_for('main.view_document', doc_id=doc_id))
    
    # PDF üret
    os.makedirs('uploads/exports', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_filename = secure_filename(document.filename.rsplit('.', 1)[0])
    output_path = os.path.join('uploads/exports', f'EduScan_{safe_filename}_{timestamp}.pdf')
    
    try:
        generate_questions_pdf(document, topic_data, output_path)
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f'EduScan_Sorular_{safe_filename}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'PDF oluşturulurken hata: {str(e)}', 'error')
        return redirect(url_for('main.view_document', doc_id=doc_id))


@main.route('/documents')
@login_required
def list_documents():
    documents = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc()).all()
    return render_template('documents.html', documents=documents)

@main.route('/document/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Bir dökümanı ve ona bağlı tüm verileri siler."""
    document = Document.query.get_or_404(doc_id)
    
    # Sadece kendi dökümanını silebilir
    if document.user_id != current_user.id:
        flash('Bu dokümanı silme yetkiniz yok.', 'error')
        return redirect(url_for('main.list_documents'))
    
    try:
        # Bağlı Topic ve Question'ları sil (cascade)
        topics = Topic.query.filter_by(document_id=doc_id).all()
        for topic in topics:
            # Her topic'in soruları
            Question.query.filter_by(topic_id=topic.id).delete()
            db.session.delete(topic)
        
        # Document kaydını sil
        document_filename = document.filename
        db.session.delete(document)
        db.session.commit()
        
        # İlgili dosyaları diskten sil (best-effort)
        try:
            for folder in ['uploads/pdfs', 'uploads/images']:
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        if document_filename in f:
                            os.remove(os.path.join(folder, f))
        except Exception as file_err:
            print(f"Dosya silme uyarısı (önemsiz): {file_err}")
        
        flash(f'"{document_filename}" başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Silme sırasında hata: {str(e)}', 'error')
    
    return redirect(url_for('main.list_documents'))

@main.route('/about')
def about():
    """Hakkında sayfası."""
    return render_template('about.html')

# ═══════════════════════════════════════════
# FEEDBACK ROUTES
# ═══════════════════════════════════════════

@main.route('/api/feedback/submit', methods=['POST'])
@login_required
def submit_feedback():
    """Bir soruya geri bildirim gönder."""
    from flask import jsonify
    
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        rating = data.get('rating')  # 'positive' veya 'negative'
        reason = data.get('reason')
        comment = data.get('comment', '')
        
        # Validation
        if not question_id or not rating:
            return jsonify({'success': False, 'error': 'Eksik parametreler'}), 400
        
        if rating not in ('positive', 'negative'):
            return jsonify({'success': False, 'error': 'Geçersiz rating'}), 400
        
        # Soruyu kontrol et
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'success': False, 'error': 'Soru bulunamadı'}), 404
        
        # Konu kategorisini al
        topic = Topic.query.get(question.topic_id)
        topic_name = topic.topic_name if topic else 'Bilinmeyen'
        
        # Mevcut feedback var mı?
        existing = Feedback.query.filter_by(
            user_id=current_user.id,
            question_id=question_id
        ).first()
        
        if existing:
            # Güncelle
            existing.rating = rating
            existing.reason = reason
            existing.comment = comment
            existing.topic_category = topic_name
            db.session.commit()
            return jsonify({
                'success': True,
                'updated': True,
                'message': 'Geri bildiriminiz güncellendi'
            })
        else:
            # Yeni kayıt
            feedback = Feedback(
                user_id=current_user.id,
                question_id=question_id,
                rating=rating,
                reason=reason,
                comment=comment,
                topic_category=topic_name
            )
            db.session.add(feedback)
            db.session.commit()
            return jsonify({
                'success': True,
                'created': True,
                'message': 'Geri bildiriminiz kaydedildi'
            })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Feedback hatası: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/api/feedback/get/<int:question_id>')
@login_required
def get_feedback(question_id):
    """Bir soru için mevcut kullanıcının feedback'ini al."""
    from flask import jsonify
    
    feedback = Feedback.query.filter_by(
        user_id=current_user.id,
        question_id=question_id
    ).first()
    
    if feedback:
        return jsonify({
            'success': True,
            'has_feedback': True,
            'rating': feedback.rating,
            'reason': feedback.reason,
            'comment': feedback.comment
        })
    else:
        return jsonify({
            'success': True,
            'has_feedback': False
        })


@main.route('/api/feedback/stats')
@login_required
def feedback_stats():
    """Geri bildirim istatistiklerini al. Gelecekte admin panel için."""
    from flask import jsonify
    
    # Toplam feedback sayısı
    total = Feedback.query.count()
    
    # Pozitif/negatif sayıları
    positive = Feedback.query.filter_by(rating='positive').count()
    negative = Feedback.query.filter_by(rating='negative').count()
    
    # Konu bazlı negatif feedback (en çok hata yapılan konular)
    topic_issues = db.session.query(
        Feedback.topic_category,
        db.func.count(Feedback.id).label('count')
    ).filter_by(rating='negative').group_by(Feedback.topic_category).order_by(
        db.func.count(Feedback.id).desc()
    ).limit(10).all()
    
    return jsonify({
        'total': total,
        'positive': positive,
        'negative': negative,
        'positive_ratio': round(positive / total * 100, 1) if total > 0 else 0,
        'top_problem_topics': [
            {'topic': t[0], 'count': t[1]} for t in topic_issues
        ]
    })
@main.route('/api/knowledge/test/<topic>')
@login_required
def test_knowledge(topic):
    """Bilgi tabanı testi (sadece debug için)."""
    from flask import jsonify
    from app.knowledge_base import get_relevant_knowledge, detect_category, list_available_categories
    
    category = detect_category(topic)
    knowledge = get_relevant_knowledge(topic)
    
    return jsonify({
        'topic': topic,
        'detected_category': category,
        'has_knowledge': bool(knowledge),
        'knowledge_length': len(knowledge),
        'knowledge_preview': knowledge[:500] if knowledge else None,
        'available_categories': list_available_categories()
    })

# ═══════════════════════════════════════════
# FAVORITE ROUTES
# ═══════════════════════════════════════════

@main.route('/api/favorite/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    """Bir soruyu favorile veya favorilerden çıkar (toggle)."""
    from flask import jsonify
    
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        
        if not question_id:
            return jsonify({'success': False, 'error': 'question_id gerekli'}), 400
        
        # Soruyu kontrol et
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'success': False, 'error': 'Soru bulunamadı'}), 404
        
        # Mevcut favori var mı?
        existing = Favorite.query.filter_by(
            user_id=current_user.id,
            question_id=question_id
        ).first()
        
        if existing:
            # Favoriden çıkar
            db.session.delete(existing)
            db.session.commit()
            return jsonify({
                'success': True,
                'is_favorite': False,
                'message': 'Favorilerden çıkarıldı'
            })
        else:
            # Favorile
            favorite = Favorite(
                user_id=current_user.id,
                question_id=question_id
            )
            db.session.add(favorite)
            db.session.commit()
            return jsonify({
                'success': True,
                'is_favorite': True,
                'message': 'Favorilere eklendi'
            })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Favori hatası: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/api/favorite/status/<int:question_id>')
@login_required
def favorite_status(question_id):
    """Bir sorunun favori durumunu kontrol et."""
    from flask import jsonify
    
    exists = Favorite.query.filter_by(
        user_id=current_user.id,
        question_id=question_id
    ).first() is not None
    
    return jsonify({
        'success': True,
        'is_favorite': exists
    })


@main.route('/favorites')
@login_required
def list_favorites():
    """Kullanıcının favori sorularını listele."""
    favorites = Favorite.query.filter_by(
        user_id=current_user.id
    ).order_by(Favorite.created_at.desc()).all()
    
    # Soru bilgilerini topla
    favorites_data = []
    for fav in favorites:
        question = Question.query.get(fav.question_id)
        if not question:
            continue
        
        topic = Topic.query.get(question.topic_id)
        document = Document.query.get(topic.document_id) if topic else None
        
        favorites_data.append({
            'favorite': fav,
            'question': question,
            'topic': topic,
            'document': document
        })
    
    return render_template('favorites.html', favorites_data=favorites_data)
# ═══════════════════════════════════════════
# FLASHCARD ROUTES
# ═══════════════════════════════════════════

@main.route('/flashcards')
@login_required
def flashcards_page():
    """Flashcard ana sayfası — çalışma seçenekleri."""
    from datetime import datetime
    
    # Toplam soru sayısı (kullanıcının tüm sorularından)
    total_questions = db.session.query(Question).join(Topic).join(Document).filter(
        Document.user_id == current_user.id
    ).count()
    
    # Bugün için hazır olanlar (zamanı gelmiş)
    due_today = db.session.query(FlashcardReview).filter(
        FlashcardReview.user_id == current_user.id,
        FlashcardReview.next_review <= datetime.now()
    ).count()
    
    # Hiç çalışılmamış olanlar
    studied_question_ids = db.session.query(FlashcardReview.question_id).filter(
        FlashcardReview.user_id == current_user.id
    ).subquery()
    
    new_count = db.session.query(Question).join(Topic).join(Document).filter(
        Document.user_id == current_user.id,
        ~Question.id.in_(studied_question_ids)
    ).count()
    
    # İstatistikler
    total_reviewed = FlashcardReview.query.filter_by(user_id=current_user.id).count()
    total_correct = db.session.query(db.func.sum(FlashcardReview.total_correct)).filter_by(
        user_id=current_user.id
    ).scalar() or 0
    total_wrong = db.session.query(db.func.sum(FlashcardReview.total_wrong)).filter_by(
        user_id=current_user.id
    ).scalar() or 0
    
    success_rate = 0
    if total_correct + total_wrong > 0:
        success_rate = round(total_correct / (total_correct + total_wrong) * 100, 1)
    
    return render_template('flashcards.html',
                           total_questions=total_questions,
                           due_today=due_today,
                           new_count=new_count,
                           total_reviewed=total_reviewed,
                           success_rate=success_rate)


@main.route('/flashcards/study')
@login_required
def flashcards_study():
    """Flashcard çalışma sayfası."""
    mode = request.args.get('mode', 'due')  # 'due', 'new', 'all', 'favorites'
    return render_template('flashcards_study.html', mode=mode)


@main.route('/api/flashcards/next')
@login_required
def flashcards_next():
    """Sıradaki kartı getir."""
    from flask import jsonify
    from datetime import datetime
    
    mode = request.args.get('mode', 'due')
    
    question = None
    
    if mode == 'due':
        # Zamanı gelmiş kartlar
        review = FlashcardReview.query.filter(
            FlashcardReview.user_id == current_user.id,
            FlashcardReview.next_review <= datetime.now()
        ).order_by(FlashcardReview.next_review.asc()).first()
        
        if review:
            question = Question.query.get(review.question_id)
    
    elif mode == 'new':
        # Hiç çalışılmamış kartlar
        studied_question_ids = db.session.query(FlashcardReview.question_id).filter(
            FlashcardReview.user_id == current_user.id
        ).subquery()
        
        question = db.session.query(Question).join(Topic).join(Document).filter(
            Document.user_id == current_user.id,
            ~Question.id.in_(studied_question_ids)
        ).order_by(db.func.random()).first()
    
    elif mode == 'favorites':
        # Favorilenmiş kartlar
        favorite_question_ids = db.session.query(Favorite.question_id).filter(
            Favorite.user_id == current_user.id
        ).subquery()
        
        question = db.session.query(Question).filter(
            Question.id.in_(favorite_question_ids)
        ).order_by(db.func.random()).first()
    
    else:  # 'all'
        # Tüm kartlar (rastgele)
        question = db.session.query(Question).join(Topic).join(Document).filter(
            Document.user_id == current_user.id
        ).order_by(db.func.random()).first()
    
    if not question:
        return jsonify({
            'success': True,
            'has_card': False,
            'message': 'Çalışılacak kart yok!'
        })
    
    # Topic bilgisini al
    topic = Topic.query.get(question.topic_id)
    
    # Favori durumu
    is_favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        question_id=question.id
    ).first() is not None
    
    # Review bilgisi
    review = FlashcardReview.query.filter_by(
        user_id=current_user.id,
        question_id=question.id
    ).first()
    
    return jsonify({
        'success': True,
        'has_card': True,
        'card': {
            'question_id': question.id,
            'question_text': question.question_text,
            'solution_steps': question.solution_steps,
            'correct_answer': question.correct_answer,
            'hint': question.hint,
            'difficulty': question.difficulty,
            'question_type': question.question_type,
            'measured_concept': question.measured_concept,
            'bloom_level': question.bloom_level,
            'topic_name': topic.topic_name if topic else 'Bilinmeyen',
            'is_favorite': is_favorite,
            'has_graph': question.has_graph,
            'graph_svg': question.graph_svg if question.has_graph else None,
        },
        'review': {
            'repetitions': review.repetitions if review else 0,
            'is_new': review is None
        }
    })


@main.route('/api/flashcards/rate', methods=['POST'])
@login_required
def flashcards_rate():
    """
    Kullanıcı kartı değerlendirdiğinde çağrılır.
    
    Rating değerleri:
    - 'again': Hiç bilmedim (1 günde tekrar)
    - 'hard': Zor hatırladım (3 günde tekrar)
    - 'good': Hatırladım (normal aralık)
    - 'easy': Kolaydı (daha uzun aralık)
    """
    from flask import jsonify
    from datetime import datetime, timedelta
    
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        rating = data.get('rating')  # 'again', 'hard', 'good', 'easy'
        
        if not question_id or rating not in ('again', 'hard', 'good', 'easy'):
            return jsonify({'success': False, 'error': 'Geçersiz parametreler'}), 400
        
        # Mevcut review'ı bul veya oluştur
        review = FlashcardReview.query.filter_by(
            user_id=current_user.id,
            question_id=question_id
        ).first()
        
        if not review:
            review = FlashcardReview(
                user_id=current_user.id,
                question_id=question_id,
                interval=1,
                ease_factor=2.5,
                repetitions=0,
                total_correct=0,
                total_wrong=0
            )
            db.session.add(review)
        if review.interval is None:
            review.interval = 1
        if review.ease_factor is None:
            review.ease_factor = 2.5
        if review.repetitions is None:
            review.repetitions = 0
        if review.total_correct is None:
            review.total_correct = 0
        if review.total_wrong is None:
            review.total_wrong = 0
        
        # SM-2 algoritmasının basitleştirilmiş versiyonu
        # Rating'e göre yeni interval hesapla
        
        if rating == 'again':
            review.interval = 1
            review.ease_factor = max(1.3, review.ease_factor - 0.2)
            review.repetitions = 0
            review.total_wrong += 1
        elif rating == 'hard':
            review.interval = max(1, int(review.interval * 1.2))
            review.ease_factor = max(1.3, review.ease_factor - 0.15)
            review.repetitions += 1
            review.total_correct += 1
        elif rating == 'good':
            if review.repetitions == 0:
                review.interval = 1
            elif review.repetitions == 1:
                review.interval = 6
            else:
                review.interval = int(review.interval * review.ease_factor)
            review.repetitions += 1
            review.total_correct += 1
        elif rating == 'easy':
            if review.repetitions == 0:
                review.interval = 4
            elif review.repetitions == 1:
                review.interval = 7
            else:
                review.interval = int(review.interval * review.ease_factor * 1.3)
            review.ease_factor = min(2.8, review.ease_factor + 0.15)
            review.repetitions += 1
            review.total_correct += 1
        
        # Sonraki tekrar tarihi
        review.next_review = datetime.now() + timedelta(days=review.interval)
        review.last_reviewed = datetime.now()
        review.last_rating = rating
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'next_interval_days': review.interval,
            'next_review': review.next_review.strftime('%d.%m.%Y'),
            'total_correct': review.total_correct,
            'total_wrong': review.total_wrong
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Flashcard rate hatası: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@main.route('/api/flashcards/stats')
@login_required
def flashcards_stats():
    """Kullanıcının flashcard istatistikleri."""
    from flask import jsonify
    from datetime import datetime, timedelta
    
    # Bu hafta çalışılanlar
    week_ago = datetime.now() - timedelta(days=7)
    weekly_reviews = FlashcardReview.query.filter(
        FlashcardReview.user_id == current_user.id,
        FlashcardReview.last_reviewed >= week_ago
    ).count()
    
    # Toplam
    total_reviews = FlashcardReview.query.filter_by(user_id=current_user.id).count()
    
    return jsonify({
        'weekly_reviews': weekly_reviews,
        'total_reviews': total_reviews
    })
# ═══════════════════════════════════════════
# DASHBOARD / STATISTICS API
# ═══════════════════════════════════════════

@main.route('/dashboard')
@login_required
def dashboard():
    """İstatistik dashboard sayfası."""
    return render_template('dashboard.html')


@main.route('/api/stats/dashboard')
@login_required
def dashboard_stats():
    """Kullanıcının tüm istatistiklerini döndürür."""
    from flask import jsonify
    from datetime import datetime, timedelta
    
    user_id = current_user.id
    
    # ═══ TEMEL İSTATİSTİKLER ═══
    
    # Toplam PDF/Doküman
    total_documents = Document.query.filter_by(user_id=user_id).count()
    
    # Toplam soru (kullanıcının dokümanlarına ait)
    total_questions = db.session.query(Question).join(Topic).join(Document).filter(
        Document.user_id == user_id
    ).count()
    
    # Doğrulanmış soru sayısı
    verified_questions = db.session.query(Question).join(Topic).join(Document).filter(
        Document.user_id == user_id,
        Question.is_verified == True
    ).count()
    
    # Favori sayısı
    total_favorites = Favorite.query.filter_by(user_id=user_id).count()
    
    # Flashcard istatistikleri
    total_reviews = FlashcardReview.query.filter_by(user_id=user_id).count()
    total_correct = db.session.query(
        db.func.sum(FlashcardReview.total_correct)
    ).filter_by(user_id=user_id).scalar() or 0
    total_wrong = db.session.query(
        db.func.sum(FlashcardReview.total_wrong)
    ).filter_by(user_id=user_id).scalar() or 0
    
    accuracy = 0
    if total_correct + total_wrong > 0:
        accuracy = round(total_correct / (total_correct + total_wrong) * 100, 1)
    
    # ═══ ÇALIŞMA SERİSİ (STREAK) ═══
    
    # Son 30 günde hangi günlerde çalışma yapılmış?
    thirty_days_ago = datetime.now() - timedelta(days=30)
    review_dates = db.session.query(
        db.func.date(FlashcardReview.last_reviewed).label('date')
    ).filter(
        FlashcardReview.user_id == user_id,
        FlashcardReview.last_reviewed >= thirty_days_ago
    ).distinct().all()
    
    unique_dates = sorted([d[0] for d in review_dates if d[0]], reverse=True)
    
    # Streak hesapla
    current_streak = 0
    if unique_dates:
        today = datetime.now().date()
        check_date = today
        
        for date_str in unique_dates:
            if isinstance(date_str, str):
                review_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                review_date = date_str
            
            if review_date == check_date or review_date == check_date - timedelta(days=1):
                current_streak += 1
                check_date = review_date - timedelta(days=1)
            else:
                break
    
    # ═══ HAFTALIK AKTIVITE ═══
    
    weekly_activity = []
    today = datetime.now().date()
    
    for i in range(6, -1, -1):  # Son 7 gün (geçmişten bugüne)
        target_date = today - timedelta(days=i)
        
        # O gün kaç flashcard çalışıldı
        flashcard_count = db.session.query(FlashcardReview).filter(
            FlashcardReview.user_id == user_id,
            db.func.date(FlashcardReview.last_reviewed) == target_date.strftime('%Y-%m-%d')
        ).count()
        
        # O gün kaç PDF yüklendi
        doc_count = db.session.query(Document).filter(
            Document.user_id == user_id,
            db.func.date(Document.uploaded_at) == target_date.strftime('%Y-%m-%d')
        ).count()
        
        # Türkçe gün adı
        day_names_tr = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
        day_name = day_names_tr[target_date.weekday()]
        
        weekly_activity.append({
            'date': target_date.strftime('%d.%m'),
            'day_name': day_name,
            'flashcards': flashcard_count,
            'documents': doc_count,
            'total': flashcard_count + doc_count,
            'is_today': target_date == today
        })
    
    # ═══ KONU BAZLI PERFORMANS ═══
    
    # En çok soru içeren konular
    top_topics = db.session.query(
        Topic.topic_name,
        db.func.count(Question.id).label('question_count')
    ).join(Question).join(Document).filter(
        Document.user_id == user_id
    ).group_by(Topic.topic_name).order_by(
        db.func.count(Question.id).desc()
    ).limit(5).all()
    
    topics_data = [
        {'name': t[0][:40] + ('...' if len(t[0]) > 40 else ''), 
         'count': t[1]} 
        for t in top_topics
    ]
    
    # ═══ ZORLUK DAĞILIMI ═══
    
    difficulty_dist = db.session.query(
        Question.difficulty,
        db.func.count(Question.id).label('count')
    ).join(Topic).join(Document).filter(
        Document.user_id == user_id
    ).group_by(Question.difficulty).all()
    
    difficulty_data = {
        'kolay': 0,
        'orta': 0,
        'zor': 0
    }
    for d in difficulty_dist:
        if d[0] in difficulty_data:
            difficulty_data[d[0]] = d[1]
    
    # ═══ BLOOM DAĞILIMI ═══
    
    bloom_dist = db.session.query(
        Question.bloom_level,
        db.func.count(Question.id).label('count')
    ).join(Topic).join(Document).filter(
        Document.user_id == user_id,
        Question.bloom_level != None
    ).group_by(Question.bloom_level).all()
    
    bloom_data = {
        'hatirlama': 0, 'anlama': 0, 'uygulama': 0,
        'analiz': 0, 'degerlendirme': 0, 'yaratma': 0
    }
    for b in bloom_dist:
        if b[0] in bloom_data:
            bloom_data[b[0]] = b[1]
    
    # ═══ ACHIEVEMENT'LAR ═══
    
    achievements = []
    
    # İlk PDF
    if total_documents >= 1:
        achievements.append({
            'id': 'first_pdf',
            'icon': '📄',
            'title': 'İlk Adım',
            'description': 'İlk PDF\'ini yükledin!',
            'unlocked': True
        })
    
    # 10 Soru
    if total_questions >= 10:
        achievements.append({
            'id': 'ten_questions',
            'icon': '🎯',
            'title': '10 Soru Kahramanı',
            'description': '10 soru ürettin',
            'unlocked': True
        })
    
    # 50 Soru
    if total_questions >= 50:
        achievements.append({
            'id': 'fifty_questions',
            'icon': '⭐',
            'title': 'Soru Ustası',
            'description': '50 soru ürettin',
            'unlocked': True
        })
    
    # İlk Favori
    if total_favorites >= 1:
        achievements.append({
            'id': 'first_favorite',
            'icon': '❤️',
            'title': 'Favori Avcısı',
            'description': 'İlk favoriligini ekledin',
            'unlocked': True
        })
    
    # İlk Flashcard
    if total_reviews >= 1:
        achievements.append({
            'id': 'first_review',
            'icon': '🎴',
            'title': 'Flashcard Başlangıç',
            'description': 'İlk flashcard çalışman',
            'unlocked': True
        })
    
    # 3 Günlük Seri
    if current_streak >= 3:
        achievements.append({
            'id': 'streak_3',
            'icon': '🔥',
            'title': '3 Günlük Seri',
            'description': '3 gün üst üste çalıştın!',
            'unlocked': True
        })
    
    # 7 Günlük Seri
    if current_streak >= 7:
        achievements.append({
            'id': 'streak_7',
            'icon': '🏆',
            'title': '1 Haftalık Seri',
            'description': 'Tam 7 gün çalıştın!',
            'unlocked': True
        })
    
    # Yüksek doğruluk
    if accuracy >= 80 and total_reviews >= 10:
        achievements.append({
            'id': 'high_accuracy',
            'icon': '🎓',
            'title': 'Akademisyen',
            'description': '%80+ başarı oranı yakaladın',
            'unlocked': True
        })
    
    # Tüm Bloom seviyeleri
    used_blooms = sum(1 for v in bloom_data.values() if v > 0)
    if used_blooms >= 4:
        achievements.append({
            'id': 'bloom_explorer',
            'icon': '🌟',
            'title': 'Bloom Kaşifi',
            'description': '4+ farklı Bloom seviyesinde sorular',
            'unlocked': True
        })
    
    # ═══ SON AKTİVİTELER ═══
    
    recent_documents = Document.query.filter_by(user_id=user_id).order_by(
        Document.uploaded_at.desc()
    ).limit(5).all()
    
    recent_docs_data = []
    for doc in recent_documents:
        question_count = db.session.query(Question).join(Topic).filter(
            Topic.document_id == doc.id
        ).count()
        
        recent_docs_data.append({
            'id': doc.id,
            'filename': doc.filename[:50] + ('...' if len(doc.filename) > 50 else ''),
            'uploaded_at': doc.uploaded_at.strftime('%d.%m.%Y'),
            'question_count': question_count
        })
    
    return jsonify({
        'success': True,
        'stats': {
            # Temel
            'total_documents': total_documents,
            'total_questions': total_questions,
            'verified_questions': verified_questions,
            'total_favorites': total_favorites,
            'total_reviews': total_reviews,
            'accuracy': accuracy,
            'current_streak': current_streak,
            
            # Grafikler
            'weekly_activity': weekly_activity,
            'top_topics': topics_data,
            'difficulty_distribution': difficulty_data,
            'bloom_distribution': bloom_data,
            
            # Diğer
            'achievements': achievements,
            'recent_documents': recent_docs_data
        }
    })
# ═══════════════════════════════════════════
# FLOATING WIDGET - ACTIVE JOBS API
# ═══════════════════════════════════════════

@main.route('/api/jobs/active')
@login_required
def get_active_jobs():
    """Kullanıcının aktif/tamamlanan ama henüz görmediği işlerini döndürür."""
    from flask import jsonify
    import traceback
    
    try:
        # Tüm aktif veya görülmemiş işleri al
        active_statuses = ['analyzing', 'generating', 'queued']
        
        # Önce sadece aktif olanları al (basit sorgu)
        active_jobs = ProcessingJob.query.filter(
            ProcessingJob.user_id == current_user.id,
            ProcessingJob.status.in_(active_statuses)
        ).order_by(ProcessingJob.id.desc()).limit(10).all()
        
        # Sonra tamamlanmış ama görülmemişleri al
        # user_notified field varsa filtrele, yoksa pas geç
        unseen_jobs = []
        try:
            unseen_jobs = ProcessingJob.query.filter(
                ProcessingJob.user_id == current_user.id,
                ProcessingJob.status.in_(['completed', 'error']),
                ProcessingJob.user_notified == False
            ).order_by(ProcessingJob.id.desc()).limit(5).all()
        except Exception as e:
            # user_notified yoksa, sessizce geç
            print(f"⚠️ user_notified field yok mu? {e}")
            unseen_jobs = []
        
        all_jobs = active_jobs + unseen_jobs
        
        jobs_data = []
        for job in all_jobs:
            # Filename al (güvenli)
            filename = "Doküman"
            try:
                if job.document_id:
                    doc = Document.query.get(job.document_id)
                    if doc and doc.filename:
                        filename = doc.filename
                elif hasattr(job, 'file_path') and job.file_path:
                    import os
                    filename = os.path.basename(job.file_path)
            except Exception:
                filename = "Doküman"
            
            if len(filename) > 40:
                filename = filename[:37] + '...'
            
            jobs_data.append({
                'job_id': str(job.id),
                'status': job.status or 'unknown',
                'progress': job.progress or 0,
                'current_step': job.current_step or 'İşleniyor...',
                'filename': filename,
                'document_id': job.document_id,
                'detected_topic': job.detected_topic,
                'error_message': job.error_message,
                'is_active': job.status in active_statuses
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_data,
            'has_active': any(j['is_active'] for j in jobs_data),
            'has_completed': any(not j['is_active'] for j in jobs_data)
        })
    
    except Exception as e:
        # Tüm hataları yakala
        error_traceback = traceback.format_exc()
        print(f"\n❌ /api/jobs/active HATASI:\n{error_traceback}\n")
        
        # Kullanıcıya boş cevap dön (UI bozulmasın)
        return jsonify({
            'success': True,
            'jobs': [],
            'has_active': False,
            'has_completed': False
        })


@main.route('/api/jobs/mark-seen/<job_id>', methods=['POST'])
@login_required
def mark_job_seen(job_id):
    """Bir işin bildirimini 'görüldü' olarak işaretle."""
    from flask import jsonify
    
    try:
        job = ProcessingJob.query.filter_by(
            id=job_id,
            user_id=current_user.id
        ).first()
        
        if job:
            try:
                job.user_notified = True
                db.session.commit()
            except Exception:
                # user_notified yoksa pas geç
                db.session.rollback()
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'İş bulunamadı'}), 404
    except Exception as e:
        import traceback
        print(f"\n❌ mark_job_seen HATASI:\n{traceback.format_exc()}\n")
        return jsonify({'success': False, 'error': str(e)}), 500