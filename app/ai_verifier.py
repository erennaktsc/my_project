"""
EduScan AI Self-Verification
=============================

Üretilen soruları ikinci bir AI çağrısıyla doğrular.
Pedagojik, mantıksal ve matematiksel hataları yakalar.
"""
import json
from collections import defaultdict
from app.ai_service import client, GENERATION_MODEL, call_with_retry, parse_json_response
from google.genai import types


# Telemetri
verification_stats = defaultdict(int)


# ═══════════════════════════════════════════
# DOĞRULAMA ŞEMASI
# ═══════════════════════════════════════════

VERIFICATION_SCHEMA = {
    "type": "object",
    "required": ["soru_dogrulamalari"],
    "properties": {
        "soru_dogrulamalari": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["soru_indeksi", "dogru", "guven_seviyesi", "aciklama"],
                "properties": {
                    "soru_indeksi": {"type": "integer"},
                    "dogru": {"type": "boolean"},
                    "guven_seviyesi": {
                        "type": "string",
                        "enum": ["yuksek", "orta", "dusuk"]
                    },
                    "aciklama": {"type": "string"},
                    "tespit_edilen_hatalar": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }
}


def build_verification_prompt(questions_data):
    """
    Doğrulama için prompt oluşturur.
    
    Args:
        questions_data: liste, her eleman bir soru dict'i
    """
    prompt = """Sen 30+ yıl deneyimli bir üniversite matematik/fizik profesörüsün.
Görevin: Aşağıdaki sorular ve çözümlerini AKADEMİK BİR HAKEM gibi kontrol etmek.

═══ KONTROL EDİLECEK SORULAR ═══

"""
    
    for idx, q in enumerate(questions_data, start=1):
        prompt += f"""
─── SORU {idx} ───
TİP: {q.get('soru_tipi', 'belirsiz')}
ZORLUK: {q.get('zorluk', 'belirsiz')}
ÖLÇÜLEN: {q.get('olculen_kavram', 'belirsiz')}

SORU METNİ:
{q.get('soru_metni', '')}

ÇÖZÜM ADIMLARI:
"""
        cozum_adimlari = q.get('cozum_adimlari', [])
        if isinstance(cozum_adimlari, list):
            for step_idx, step in enumerate(cozum_adimlari, start=1):
                prompt += f"  {step_idx}. {step}\n"
        else:
            prompt += f"  {cozum_adimlari}\n"
        
        prompt += f"""
DOĞRU CEVAP:
{q.get('dogru_cevap', '')}

"""
    
    prompt += """
═══ KONTROL KURALLARI ═══

Her soru için şunları kontrol et:

1. ✅ MATEMATİKSEL DOĞRULUK:
   - Hesaplamalar doğru mu?
   - İşaretler (+/-) doğru mu?
   - Formüller doğru uygulanmış mı?

2. ✅ MANTIKSAL TUTARLILIK:
   - Çözüm adımları mantıklı sıralanmış mı?
   - Bir adımdan diğerine geçiş net mi?
   - Eksik adım var mı?

3. ✅ SORU-CEVAP UYUMU:
   - Cevap sorunun aslında istediği şey mi?
   - Birim doğru mu? (örn: m/s vs km/h)

4. ✅ PEDAGOJİK KALİTE (İspat/Yorum için):
   - İspat tam mı?
   - Tüm durumlar kapsanmış mı?
   - Açıklama anlaşılır mı?

═══ ÇIKTI FORMATI (JSON) ═══

Her soru için tek tek değerlendir:

{
  "soru_dogrulamalari": [
    {
      "soru_indeksi": 1,
      "dogru": true,
      "guven_seviyesi": "yuksek",
      "aciklama": "Hesaplama ve mantık doğru. Adımlar net.",
      "tespit_edilen_hatalar": []
    },
    {
      "soru_indeksi": 2,
      "dogru": false,
      "guven_seviyesi": "yuksek",
      "aciklama": "Türev hesabında işaret hatası var.",
      "tespit_edilen_hatalar": [
        "Adım 2: (-1)^3 = -1, fakat çözümde +1 olarak alınmış",
        "Sonuç olarak doğru cevap +4 değil -4 olmalı"
      ]
    }
  ]
}

⚠️ KRİTİK KURALLAR:
- Her soruyu detaylı incele
- Şüphen varsa "guven_seviyesi" = "orta" veya "dusuk" yaz
- Sadece KESİN hata varsa "dogru": false yap
- Küçük yazım/format hatalarını "dogru" yap, sadece pedagojik notu ver
- SADECE JSON dön, başka açıklama yok"""

    return prompt


# ═══════════════════════════════════════════
# DOĞRULAMA FONKSIYONU
# ═══════════════════════════════════════════

def verify_questions_batch(questions_data):
    """
    Bir batch soruyu AI ile doğrular.
    
    Args:
        questions_data: liste, sorular
    
    Returns:
        liste, her soru için doğrulama sonucu:
        [
            {
                'index': 0,
                'verified': True,
                'confidence': 'yuksek',
                'message': '...',
                'errors': []
            },
            ...
        ]
    """
    if not questions_data:
        return []
    
    print(f"\n🔍 AI doğrulama başlıyor: {len(questions_data)} soru kontrol edilecek...")
    
    prompt = build_verification_prompt(questions_data)
    
    # Structured output config
    config = {
        'response_mime_type': 'application/json',
        'response_schema': VERIFICATION_SCHEMA
    }
    
    try:
        response = call_with_retry(
            lambda: client.models.generate_content(
                model=GENERATION_MODEL,
                contents=prompt,
                config=config
            ),
            max_retries=3,
            context="ai_verification"
        )
        
        verification_data = parse_json_response(response.text)
        soru_dogrulamalari = verification_data.get('soru_dogrulamalari', [])
        
        # Sonuçları işle
        results = []
        for verification in soru_dogrulamalari:
            soru_idx = verification.get('soru_indeksi', 0) - 1  # 1-based to 0-based
            
            if 0 <= soru_idx < len(questions_data):
                result = {
                    'index': soru_idx,
                    'verified': verification.get('dogru', False),
                    'confidence': verification.get('guven_seviyesi', 'dusuk'),
                    'message': verification.get('aciklama', ''),
                    'errors': verification.get('tespit_edilen_hatalar', [])
                }
                results.append(result)
                
                # Telemetri
                if result['verified']:
                    verification_stats['verified'] += 1
                else:
                    verification_stats['rejected'] += 1
                
                # Log
                status = "✅" if result['verified'] else "❌"
                print(f"   {status} Soru {soru_idx + 1}: {result['confidence']} güven - {result['message'][:80]}")
        
        print(f"✅ Doğrulama tamamlandı: {sum(1 for r in results if r['verified'])}/{len(results)} doğru\n")
        
        return results
        
    except Exception as e:
        print(f"⚠️ AI doğrulama hatası: {e}")
        verification_stats['error'] += 1
        
        # Hata durumunda boş liste dön — sistem çalışmaya devam etsin
        return []


def get_verification_summary(verification_results):
    """
    Doğrulama sonuçlarından özet üretir.
    """
    if not verification_results:
        return {
            'total': 0,
            'verified': 0,
            'rejected': 0,
            'verification_rate': 0
        }
    
    total = len(verification_results)
    verified = sum(1 for r in verification_results if r['verified'])
    
    return {
        'total': total,
        'verified': verified,
        'rejected': total - verified,
        'verification_rate': round(verified / total * 100, 1) if total > 0 else 0
    }


# ═══════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════

def run_self_test():
    """Test amaçlı."""
    print("\n═══ EduScan AI Verifier Self-Test ═══\n")
    
    test_questions = [
        {
            'soru_metni': '$f(x) = x^2 + 3x$ fonksiyonunun türevini bulun.',
            'soru_tipi': 'turetme',
            'zorluk': 'kolay',
            'olculen_kavram': 'Polinom türevi',
            'cozum_adimlari': [
                'Adım 1: Toplam kuralı uygulanır: (f+g)\' = f\' + g\'',
                'Adım 2: Güç kuralı: d/dx(x²) = 2x',
                'Adım 3: Sabit çarpan kuralı: d/dx(3x) = 3'
            ],
            'dogru_cevap': '$f\'(x) = 2x + 3$'
        },
        {
            'soru_metni': '$\\int_0^1 x^2 dx$ integralini hesaplayın.',
            'soru_tipi': 'hesaplama',
            'zorluk': 'kolay',
            'olculen_kavram': 'Belirli integral',
            'cozum_adimlari': [
                'Adım 1: Güç kuralı: ∫x^n dx = x^(n+1)/(n+1)',
                'Adım 2: ∫x² dx = x³/3',
                'Adım 3: Sınırları yerleştir: [x³/3] from 0 to 1 = 1/3 - 0 = 1/3'
            ],
            'dogru_cevap': '$\\frac{1}{3}$'
        }
    ]
    
    results = verify_questions_batch(test_questions)
    
    print("\n📊 ÖZET:")
    summary = get_verification_summary(results)
    print(f"   Toplam: {summary['total']}")
    print(f"   Doğrulandı: {summary['verified']}")
    print(f"   Reddedildi: {summary['rejected']}")
    print(f"   Başarı oranı: {summary['verification_rate']}%")


if __name__ == '__main__':
    run_self_test()