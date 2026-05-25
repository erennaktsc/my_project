from app import create_app
from app.models import User, Document, Topic, Question

app = create_app()

with app.app_context():
    print("\n" + "="*70)
    print("VERİTABANI İÇERİĞİ")
    print("="*70)
    
    # Kullanıcılar
    print("\n📁 KULLANICILAR:")
    users = User.query.all()
    for u in users:
        print(f"  [{u.id}] {u.username} ({u.email})")
    
    # Dökümanlar
    print("\n📄 DÖKÜMANLAR:")
    docs = Document.query.all()
    for d in docs:
        print(f"  [{d.id}] {d.filename}")
        print(f"      Tür: {d.file_type} | Yüklenme: {d.uploaded_at}")
        print(f"      Çıkarılan metin (ilk 200 karakter): {d.extracted_text[:200]}...")
    
    # Konular
    print("\n📚 KONULAR:")
    topics = Topic.query.all()
    for t in topics:
        print(f"  [{t.id}] {t.topic_name}")
        print(f"      Özet: {t.summary}")
    
    # Sorular
    print("\n❓ SORULAR:")
    questions = Question.query.all()
    for q in questions:
        print(f"\n  [{q.id}] Konu ID: {q.topic_id} | Zorluk: {q.difficulty} | Tip: {q.question_type}")
        print(f"  SORU: {q.question_text[:300]}...")
        print(f"  ÇÖZÜM:")
        for line in q.solution_steps.split('\n'):
            print(f"    • {line}")
    
    print("\n" + "="*70)
    print(f"TOPLAM: {len(users)} kullanıcı, {len(docs)} döküman, {len(topics)} konu, {len(questions)} soru")
    print("="*70 + "\n")