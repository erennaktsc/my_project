import os
import shutil
import threading
import json as json_lib
from datetime import datetime
from app.ai_service import get_friendly_error
from app.models import db, ProcessingJob, Document, Topic, Question
from app.ai_service import analyze_document, generate_questions, parse_json_response
from app.source_extractor import pdf_to_page_images, image_to_page_image, crop_question_region, save_full_page_as_source
from app.ai_verifier import verify_questions_batch, get_verification_summary
from app.math_verifier import verify_question as sympy_verify_question
from app.graph_generator import generate_graph
from app.graph_extractor import auto_generate_graph_data

def update_job(app, job_id, **fields):
    """Job durumunu thread-safe şekilde günceller."""
    with app.app_context():
        job = ProcessingJob.query.get(job_id)
        if not job:
            return
        for key, value in fields.items():
            setattr(job, key, value)
        db.session.commit()


def process_in_background(app, job_id, image_path, user_id, num_questions=3, bloom_levels=None):
    """
    Bir görüntüyü/PDF'i arka planda işler.
    Her adımda ProcessingJob'u günceller, frontend SSE ile bunu alır.
    """
    try:
        update_job(app, job_id, 
                   status='analyzing', 
                   current_step='Dosya hazırlanıyor...', 
                   progress=5)
        
        # Dosyayı uygun klasöre kopyala
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
        
        # Sayfa görüntülerini çıkar
        update_job(app, job_id, 
                   current_step='Sayfalar görüntüye çevriliyor...', 
                   progress=10)
        
        if file_type == 'pdf':
            page_images = pdf_to_page_images(image_path)
        else:
            page_images = image_to_page_image(image_path)
        
        total_pages = len(page_images)
        page_map = {page_no: path for page_no, path in page_images}
        
        update_job(app, job_id, 
                   current_step=f'{total_pages} sayfa hazırlandı. Yapay zeka analiz ediyor...', 
                   progress=20)
        
        # AI analizi
        analysis_raw = analyze_document(image_path)
        analysis = parse_json_response(analysis_raw)
        
        detected_topic = analysis.get('konu', 'Bilinmeyen')
        alt_basliklar = analysis.get('alt_basliklar', [])
        seviye = analysis.get('zorluk_seviyesi', 'belirsiz')
        icerik_tipi = analysis.get('icerik_tipi', 'karisik')
        
        update_job(app, job_id,
                   current_step=f'Konu tespit edildi: {detected_topic}',
                   progress=45,
                   detected_topic=detected_topic,
                   detected_subtopics=json_lib.dumps(alt_basliklar, ensure_ascii=False),
                   detected_level=seviye,
                   content_type=icerik_tipi)
        
        # Document ve Topic kayıtlarını oluştur
        with app.app_context():
            document = Document(
                user_id=user_id,
                filename=new_filename,
                file_type=file_type,
                extracted_text=analysis.get('ham_metin', '')
            )
            db.session.add(document)
            db.session.flush()
            
            topic = Topic(
                document_id=document.id,
                topic_name=detected_topic,
                summary=analysis.get('ozet', ''),
                subtopics=json_lib.dumps(alt_basliklar, ensure_ascii=False),
                prerequisites=json_lib.dumps(analysis.get('on_gereksinimler', []), ensure_ascii=False),
                common_mistakes=json_lib.dumps(analysis.get('tipik_hatalar', []), ensure_ascii=False),
                difficulty_level=seviye
            )
            db.session.add(topic)
            db.session.flush()
            
            document_id = document.id
            topic_id = topic.id
            db.session.commit()
        
        update_job(app, job_id,
                   status='generating',
                   current_step='Akademik sorular ve kaynak referansları üretiliyor...',
                   progress=60,
                   document_id=document_id)
        
        # Soruları üret (try-except ile koruma altında)
        topic_data = {
            'konu': detected_topic,
            'ozet': analysis.get('ozet'),
            'anahtar_kavramlar': analysis.get('anahtar_kavramlar', []),
            'alt_basliklar': alt_basliklar,
            'on_gereksinimler': analysis.get('on_gereksinimler', []),
            'tipik_hatalar': analysis.get('tipik_hatalar', []),
            'total_pages': total_pages
        }
        
        try:
            questions_raw = generate_questions(
                topic_data, 
                num_questions=num_questions, 
                has_pages=True,
                bloom_levels=bloom_levels  # YENİ
            )
            questions_data = parse_json_response(questions_raw)
        except Exception as gen_error:
            raise Exception(
                f"Soru üretilirken hata oluştu: {str(gen_error)}. "
                "Yapay zeka modeli şu an yoğun olabilir. Lütfen birkaç dakika sonra tekrar deneyin."
            )
        
        update_job(app, job_id,
                   current_step='Kaynak görüntüler kırpılıyor...',
                   progress=85)
        
        # Soruları kaydet
        with app.app_context():
            sorular = questions_data.get('sorular', [])
            
            # Boş kontrolü
            if not sorular:
                raise Exception(
                    "Yapay zeka soru üretemedi. PDF içeriği yetersiz olabilir veya model yoğun. "
                    "Farklı bir PDF deneyin veya birkaç dakika sonra tekrar deneyin."
                )
            # ═══ YENİ: AI ile doğrulama ═══
            update_job(app, job_id,
                       current_step='Sorular yapay zeka ile doğrulanıyor...',
                       progress=88)
            
            try:
                verification_results = verify_questions_batch(sorular)
                summary = get_verification_summary(verification_results)
                
                print(f"📊 Doğrulama özeti: {summary['verified']}/{summary['total']} doğru ({summary['verification_rate']}%)")
                
                # Her soru için doğrulama sonucunu hazırla (index ile eşleştir)
                verification_map = {r['index']: r for r in verification_results}
            except Exception as ve:
                print(f"⚠️ AI doğrulama atlanıyor: {ve}")
                verification_map = {}

            for soru_index, soru in enumerate(sorular):
                # ═══ DEBUG ═══
                kaynak_sayfa = soru.get('kaynak_sayfa', 0)
                kaynak_aciklama = soru.get('kaynak_aciklama', '')
                
                print(f"\n┌─── SORU DEBUG ───")
                print(f"│ kaynak_sayfa: {kaynak_sayfa}")
                print(f"│ kaynak_aciklama: {kaynak_aciklama[:100]}...")
                print(f"│ Toplam sayfa: {len(page_map)}")
                print(f"│ Mevcut sayfa numaraları: {list(page_map.keys())}")
                print(f"└──────────────────\n")
                
                # Kaynak sayfayı KIRPMADAN tam halde kaydet
                # Kaynak sayfayı KIRPMADAN tam halde kaydet
                source_image_path = None
                final_kaynak_sayfa = kaynak_sayfa
                
                # Strateji 1: AI'nın verdiği sayfa numarası varsa onu kullan
                if kaynak_sayfa and kaynak_sayfa > 0 and kaynak_sayfa in page_map:
                    page_image = page_map[kaynak_sayfa]
                    full_page_path = save_full_page_as_source(page_image)
                    if full_page_path:
                        source_image_path = full_page_path.replace('\\', '/')
                        print(f"✅ Sayfa {kaynak_sayfa} kaydedildi (AI önerisi)")
                
                # Strateji 2: AI sayfa vermedi ama PDF tek sayfaysa otomatik onu kullan
                elif len(page_map) == 1:
                    single_page_no = list(page_map.keys())[0]
                    page_image = page_map[single_page_no]
                    full_page_path = save_full_page_as_source(page_image)
                    if full_page_path:
                        source_image_path = full_page_path.replace('\\', '/')
                        final_kaynak_sayfa = single_page_no
                        print(f"✅ Tek sayfa otomatik kaydedildi: {single_page_no}")
                
                # Strateji 3: Çok sayfalı PDF ama AI geçerli sayfa vermedi → ilk sayfayı kullan
                elif len(page_map) > 1:
                    first_page_no = min(page_map.keys())
                    page_image = page_map[first_page_no]
                    full_page_path = save_full_page_as_source(page_image)
                    if full_page_path:
                        source_image_path = full_page_path.replace('\\', '/')
                        final_kaynak_sayfa = first_page_no
                        print(f"⚠️ AI geçerli sayfa vermedi (verdiği: {kaynak_sayfa}), fallback: sayfa {first_page_no}")
                
                else:
                    print(f"❌ Sayfa kaydedilemedi. kaynak_sayfa={kaynak_sayfa}, page_map boş")
                
                # Question kaydı oluştur
               # ═══ Doğrulama sonuçları ═══
                ai_verification = verification_map.get(soru_index, {})
                sympy_verification = sympy_verify_question(soru)
                
                # Hangi yöntem doğruladı?
                is_verified_by_ai = ai_verification.get('verified', False)
                is_verified_by_sympy = sympy_verification.get('verified', False)
                
                is_verified = is_verified_by_ai or is_verified_by_sympy
                
                if is_verified_by_sympy and is_verified_by_ai:
                    method = 'both'
                elif is_verified_by_sympy:
                    method = 'sympy'
                elif is_verified_by_ai:
                    method = 'ai'
                else:
                    method = None
                
                # Question kaydı oluştur
                cozum_metni = '\n'.join(soru.get('cozum_adimlari', []))

                # ═══ YENİ: Matplotlib ile grafik üret ═══
                has_graph = bool(soru.get('has_graph', False))
                graph_svg_final = ''
                graph_data_json = ''

                if has_graph:
                    graph_data = soru.get('graph_data')
                    
                    # ═══ STRATEJI 1: AI doğru veri verdi mi? ═══
                    if graph_data and isinstance(graph_data, dict) and len(graph_data) > 0 and graph_data.get('graph_type'):
                        try:
                            graph_svg_final = generate_graph(graph_data) or ''
                            graph_data_json = json_lib.dumps(graph_data, ensure_ascii=False)
                            if graph_svg_final:
                                print(f"   ✅ AI grafiği başarıyla üretti: {graph_data.get('graph_type')}")
                        except Exception as ge:
                            print(f"   ⚠️ AI verisinden grafik üretilemedi: {ge}")
                            graph_svg_final = ''

                    # ═══ STRATEJI 2: Otomatik tespit (AI başarısız olunca) ═══
                    if not graph_svg_final:
                        print(f"   🔍 AI grafik veri vermedi, otomatik tespit deneniyor...")
                        try:
                            auto_graph_data = auto_generate_graph_data(soru)
                            if auto_graph_data:
                                graph_svg_final = generate_graph(auto_graph_data) or ''
                                if graph_svg_final:
                                    graph_data_json = json_lib.dumps(auto_graph_data, ensure_ascii=False)
                                    print(f"   ✅ Otomatik tespit başarılı: {auto_graph_data.get('graph_type')} (fonksiyon: {auto_graph_data.get('function') or auto_graph_data.get('functions', [{}])[0].get('expr', '?')})")
                        except Exception as ae:
                            print(f"   ⚠️ Otomatik tespit hatası: {ae}")
                    
                    # ═══ STRATEJI 3: AI eski usul SVG verdi mi? (geriye uyumluluk) ═══
                    if not graph_svg_final and soru.get('graph_svg'):
                        graph_svg_final = soru.get('graph_svg', '')
                        print(f"   ✅ AI eski usul SVG verdi")
                    
                    # DEBUG: Neden grafik üretilemedi?
                if has_graph and not graph_svg_final:
                    gd = soru.get('graph_data')
                    if not gd:
                        print(f"   ⚠️ AI 'has_graph=true' dedi ama graph_data göndermedi")
                    elif isinstance(gd, dict) and len(gd) == 0:
                        print(f"   ⚠️ AI 'has_graph=true' dedi ama graph_data boş {{}}")
                    elif isinstance(gd, dict) and not gd.get('graph_type'):
                        print(f"   ⚠️ AI graph_type belirtmedi. Anahtarlar: {list(gd.keys())}")
                    else:
                        print(f"   ⚠️ Graph generation hatası, tip: {gd.get('graph_type', 'BİLİNMİYOR')}")
                
                if not graph_svg_final:
                    has_graph = False
                    print(f"⚠️ has_graph=true ama grafik üretilemedi, false yapıldı")

                # Question kaydı oluştur
                question = Question(
                    topic_id=topic_id,
                    question_text=soru.get('soru_metni', ''),
                    solution_steps=cozum_metni,
                    correct_answer=soru.get('dogru_cevap', ''),
                    difficulty=soru.get('zorluk', 'orta'),
                    question_type=soru.get('soru_tipi', 'hesaplama'),
                    measured_concept=soru.get('olculen_kavram', ''),
                    options=json_lib.dumps([], ensure_ascii=False),
                    hint=soru.get('ipucu', ''),
                    source_page=final_kaynak_sayfa if final_kaynak_sayfa and final_kaynak_sayfa > 0 else None,
                    source_image_path=source_image_path,
                    source_description=kaynak_aciklama,
                    # Grafik alanları — YENİ MATPLOTLIB SİSTEMİ
                    has_graph=has_graph,
                    graph_svg=graph_svg_final,
                    graph_description=soru.get('graph_description', '') or '',
                    graph_data=graph_data_json,  # YENİ
                    # Bloom Taksonomisi
                    bloom_level=soru.get('bloom_seviyesi', 'uygulama'),
                    # AI Doğrulama Alanları
                    is_verified=is_verified,
                    verification_method=method,
                    verification_confidence=ai_verification.get('confidence', 'dusuk'),
                    verification_message=ai_verification.get('message', ''),
                    verification_errors=json_lib.dumps(
                        ai_verification.get('errors', []),
                        ensure_ascii=False
                    )
                )
                db.session.add(question)
            
            db.session.commit()
        
        update_job(app, job_id,
                   status='completed',
                   current_step='Tamamlandı!',
                   progress=100)
    
    except Exception as e:
        # Kullanıcı dostu hata mesajı al
        friendly = get_friendly_error(e)
        
        user_message = f"{friendly['icon']} {friendly['title']}: {friendly['message']}"
        
        # Terminal'e teknik detay yazdır (debug için)
        print(f"\n❌ Hata kategorisi: {friendly['category']}")
        print(f"   Kullanıcıya gösterilen: {friendly['title']} - {friendly['message']}")
        print(f"   Teknik detay: {friendly['technical_details']}")
        
        # Job'u güncelle — thread-safe update_job fonksiyonunu kullan
        try:
            update_job(app, job_id, 
                       status='error', 
                       error_message=user_message)
        except Exception as update_err:
            # Eğer update_job da hata verirse log'la, ama crash etme
            print(f"⚠️ Job güncellenirken hata: {update_err}")


def start_background_job(app, job_id, image_path, user_id, num_questions=3, bloom_levels=None):
    """İşi yeni bir thread'de başlatır."""
    thread = threading.Thread(
        target=process_in_background,
        args=(app, job_id, image_path, user_id, num_questions, bloom_levels),
        daemon=True
    )
    thread.start()