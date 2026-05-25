import os
import shutil
from datetime import datetime
from app.models import db, User, Document, Topic, Question
from app.ai_service import analyze_document, generate_questions, parse_json_response
import json as json_lib


def get_or_create_default_user():
    """Test için varsayılan bir kullanıcı oluşturur veya getirir."""
    user = User.query.filter_by(username='test_user').first()
    if not user:
        user = User(
            username='test_user',
            email='test@eduscan.local',
            password_hash='test_hash_not_secure'
        )
        db.session.add(user)
        db.session.commit()
        print(f"✓ Yeni test kullanıcısı oluşturuldu (id={user.id})")
    return user

def process_document(image_path, user_id, num_questions=3):
    # user_id zorunlu — kim yüklediğini bilmemiz lazım
    if user_id is None:
        raise ValueError("process_document için user_id parametresi zorunludur")
    """
    Bir görüntüyü baştan sona işler:
    1. Dosyayı uploads/ klasörüne kopyalar
    2. AI ile analiz eder
    3. Document, Topic, Question kayıtlarını veritabanına yazar
    
    Geri dönüş: oluşturulan Document objesi
    """
    print(f"\n{'='*60}")
    print(f"DÖKÜMAN İŞLENİYOR: {image_path}")
    print(f"{'='*60}\n")
    
    # 1. Kullanıcı kontrolü
    if user_id is None:
        user = get_or_create_default_user()
        user_id = user.id
    
    # 2. Dosyayı uploads/ klasörüne kopyala
    filename = os.path.basename(image_path)
    file_ext = filename.lower().split('.')[-1]
    
    if file_ext == 'pdf':
        target_folder = 'uploads/pdfs'
        file_type = 'pdf'
    else:
        target_folder = 'uploads/images'
        file_type = 'image'
    
    os.makedirs(target_folder, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"{timestamp}_{filename}"
    target_path = os.path.join(target_folder, new_filename)
    shutil.copy(image_path, target_path)
    print(f"✓ Dosya kopyalandı: {target_path}")
    
    # 3. AI ile analiz et
    print("\n→ AI analizi başlatılıyor...")
    analysis_raw = analyze_document(image_path)
    analysis = parse_json_response(analysis_raw)
    print(f"✓ Konu tespit edildi: {analysis.get('konu')}")
    print(f"✓ İçerik tipi: {analysis.get('icerik_tipi')}")
    
    # 4. Document kaydı oluştur
    document = Document(
        user_id=user_id,
        filename=new_filename,
        file_type=file_type,
        extracted_text=analysis.get('ham_metin', '')
    )
    db.session.add(document)
    db.session.flush()  # ID alabilmek için
    print(f"✓ Document kaydı oluşturuldu (id={document.id})")
    
    # 5. Topic kaydı oluştur
    topic = Topic(
        document_id=document.id,
        topic_name=analysis.get('konu', 'Bilinmeyen Konu'),
        summary=analysis.get('ozet', ''),
        subtopics=json_lib.dumps(analysis.get('alt_basliklar', []), ensure_ascii=False),
        prerequisites=json_lib.dumps(analysis.get('on_gereksinimler', []), ensure_ascii=False),
        common_mistakes=json_lib.dumps(analysis.get('tipik_hatalar', []), ensure_ascii=False),
        difficulty_level=analysis.get('zorluk_seviyesi', 'universite_1')
    )
    db.session.add(topic)
    db.session.flush()
    print(f"✓ Topic kaydı oluşturuldu (id={topic.id})")
    
    # 6. Sorular üret
    print(f"\n→ {num_questions} soru üretiliyor (Pro model kullanılıyor, biraz uzun sürebilir)...")
    topic_data = {
        'konu': analysis.get('konu'),
        'ozet': analysis.get('ozet'),
        'anahtar_kavramlar': analysis.get('anahtar_kavramlar', []),
        'alt_basliklar': analysis.get('alt_basliklar', []),
        'on_gereksinimler': analysis.get('on_gereksinimler', []),
        'tipik_hatalar': analysis.get('tipik_hatalar', [])
    }
    questions_raw = generate_questions(topic_data, num_questions=num_questions)
    questions_data = parse_json_response(questions_raw)

    # 7. Question kayıtları oluştur
    sorular = questions_data.get('sorular', [])
    for i, soru in enumerate(sorular, start=1):
        cozum_metni = '\n'.join(soru.get('cozum_adimlari', []))
        question = Question(
            topic_id=topic.id,
            question_text=soru.get('soru_metni', ''),
            solution_steps=cozum_metni,
            correct_answer=soru.get('dogru_cevap', ''),
            difficulty=soru.get('zorluk', 'orta'),
            question_type=soru.get('soru_tipi', 'hesaplama'),
            measured_concept=soru.get('olculen_kavram', ''),
            options=json_lib.dumps(soru.get('secenekler', []), ensure_ascii=False),
            hint=soru.get('ipucu', '')
        )
        db.session.add(question)
        print(f"✓ Soru {i} kaydedildi (zorluk: {soru.get('zorluk')}, kavram: {soru.get('olculen_kavram', 'belirsiz')[:40]})")
    
    # 8. Commit
    db.session.commit()
    
    print(f"\n{'='*60}")
    print(f"✓ İŞLEM TAMAMLANDI")
    print(f"  Document: {document.id}")
    print(f"  Topic: {topic.id} ({topic.topic_name})")
    print(f"  Toplam soru: {len(sorular)}")
    print(f"{'='*60}\n")
    
    return document