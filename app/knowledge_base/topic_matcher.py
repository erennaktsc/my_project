"""
Konu Eşleştirici (Topic Matcher)
=================================

AI'nın tespit ettiği konu adını, bilgi tabanındaki kategoriyle eşleştirir.
"""
import re
from app.knowledge_base import mathematics
from app.knowledge_base import mathematics, physics

# ═══════════════════════════════════════════
# KATEGORİ KEYWORDS MAPPING
# Her kategori için tetikleyici kelimeler
# ═══════════════════════════════════════════

CATEGORY_KEYWORDS = {
    # ─── MATEMATİK ───
    'kalkulus_1': [
        'türev', 'turev', 'limit', 'süreklilik', 'sureklilik',
        'fonksiyon analizi', 'maksimum', 'minimum', 'ekstremum',
        'l\'hopital', 'lhopital', 'asimptot', 'monoton',
        'calculus 1', 'calculus i', 'kalkülüs 1', 'kalkulus 1'
    ],
    
    'kalkulus_2': [
        'integral', 'belirli integral', 'belirsiz integral',
        'integrasyon', 'kısmi integral', 'kismi integral',
        'değişken değiştirme', 'degisken degistirme',
        'seri', 'dizi', 'yakınsaklık', 'yakinsaklik',
        'taylor', 'maclaurin', 'fourier serisi',
        'calculus 2', 'calculus ii', 'kalkülüs 2', 'kalkulus 2'
    ],
    
    'kalkulus_3': [
        'çok değişkenli', 'cok degiskenli', 'multivariable',
        'kısmi türev', 'kismi turev', 'gradient', 'gradyan',
        'çift integral', 'cift integral', 'çok katlı integral',
        'cok katli integral', 'üçlü integral', 'uclu integral',
        'kutupsal koordinat', 'silindirik', 'küresel koordinat',
        'kuresel koordinat', 'jacobi', 'vektor analizi',
        'vektör analizi', 'green teoremi', 'stokes', 'divergans',
        'rotasyonel', 'curl', 'divergens',
        'calculus 3', 'calculus iii', 'kalkülüs 3', 'kalkulus 3'
    ],
    
    'lineer_cebir': [
        'matris', 'determinant', 'özdeğer', 'ozdeger', 
        'eigenvalue', 'eigenvector', 'özvektör', 'ozvektor',
        'lineer denklem', 'doğrusal denklem', 'dogrusal denklem',
        'vektör uzayı', 'vektor uzayi', 'lineer dönüşüm',
        'lineer donusum', 'taban', 'rank', 'kernel', 'çekirdek',
        'cekirdek', 'gauss eliminasyonu', 'lineer cebir',
        'linear algebra', 'doğrusal cebir', 'dogrusal cebir'
    ],
    
    'diferansiyel_denklemler': [
        'diferansiyel denklem', 'differential equation', 
        'ode', 'pde', 'kısmi diferansiyel', 'kismi diferansiyel',
        'lineer denklem', 'homojen denklem', 'özel çözüm',
        'ozel cozum', 'genel çözüm', 'genel cozum',
        'laplace dönüşümü', 'laplace donusumu',
        'başlangıç değer', 'baslangic deger', 'sınır değer',
        'sinir deger', 'wronskian'
    ],
    
    'olasilik_istatistik': [
        'olasılık', 'olasilik', 'probability', 'istatistik',
        'statistics', 'dağılım', 'dagilim', 'normal dağılım',
        'binom', 'poisson', 'beklenen değer', 'beklenen deger',
        'varyans', 'standart sapma', 'hipotez testi',
        'güven aralığı', 'guven araligi', 'bayes',
        'koşullu olasılık', 'kosullu olasilik', 'permütasyon',
        'kombinasyon', 'kombinasyon'
    ],
    
    # ─── FİZİK ───
    'klasik_mekanik': [
        'newton yasası', 'newton kanunu', 'kuvvet',
        'momentum', 'enerji', 'kinetik enerji', 'potansiyel enerji',
        'iş enerji', 'is enerji', 'work energy', 'çarpışma',
        'carpisma', 'açısal momentum', 'acisal momentum',
        'tork', 'eylemsizlik momenti', 'dönme', 'donme',
        'rotasyon', 'klasik mekanik', 'classical mechanics',
        'sürtünme', 'surtunme', 'eğik düzlem', 'egik duzlem'
    ],
    
    'elektromanyetizma': [
        'elektrik', 'manyetik', 'coulomb', 'gauss yasası',
        'gauss kanunu', 'kapasitör', 'kondansatör', 'kondansator',
        'direnç', 'akım', 'voltaj', 'gerilim', 'ohm yasası',
        'ohm kanunu', 'manyetik alan', 'elektrik alan',
        'faraday', 'lenz', 'maxwell denklemleri',
        'elektromanyetizma', 'electromagnetism', 'indüksiyon',
        'induksiyon'
    ],
    
    'termodinamik': [
        'termodinamik', 'thermodynamics', 'isı', 'sıcaklık',
        'sicaklik', 'entropi', 'entropy', 'iç enerji',
        'ic enerji', 'birinci yasa', 'ikinci yasa',
        'gaz yasası', 'ideal gaz', 'pv=nrt', 'carnot',
        'enthalpi', 'entalpi', 'serbest enerji',
        'adyabatik', 'izotermal', 'izokorik', 'izobarik'
    ],
}


# ═══════════════════════════════════════════
# BİLGİ TABANI MODÜLLERI
# ═══════════════════════════════════════════

KNOWLEDGE_MODULES = {
    # Matematik
    'kalkulus_1': mathematics.KALKULUS_1,
    'kalkulus_2': mathematics.KALKULUS_2,
    'kalkulus_3': mathematics.KALKULUS_3,
    'lineer_cebir': mathematics.LINEER_CEBIR,
    'diferansiyel_denklemler': mathematics.DIFERANSIYEL_DENKLEMLER,
    'olasilik_istatistik': mathematics.OLASILIK_ISTATISTIK,
    
    # Fizik
    'klasik_mekanik': physics.KLASIK_MEKANIK,
    'elektromanyetizma': physics.ELEKTROMANYETIZMA,
    'termodinamik': physics.TERMODINAMIK,
}


# ═══════════════════════════════════════════
# FONKSİYONLAR
# ═══════════════════════════════════════════

def normalize_text(text):
    """Karşılaştırma için metni normalize eder."""
    if not text:
        return ''
    text = text.lower()
    # Türkçe karakterleri normalize et
    replacements = {
        'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's',
        'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
    }
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    return text


def detect_category(topic_name, subtopics=None):
    """
    Verilen konu adı ve alt başlıklardan kategori tespit eder.
    
    Args:
        topic_name: AI'nın tespit ettiği ana konu
        subtopics: AI'nın çıkardığı alt başlıklar (liste)
    
    Returns:
        Kategori adı (string) veya None
    """
    if not topic_name:
        return None
    
    # Tüm metni birleştir ve normalize et
    full_text = topic_name
    if subtopics and isinstance(subtopics, list):
        full_text += ' ' + ' '.join(str(s) for s in subtopics)
    
    normalized = normalize_text(full_text)
    
    # Her kategori için skor hesapla
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)
            if normalized_keyword in normalized:
                # Tam kelime eşleşmesi daha değerli
                if re.search(r'\b' + re.escape(normalized_keyword) + r'\b', normalized):
                    score += 3
                else:
                    score += 1
        if score > 0:
            scores[category] = score
    
    if not scores:
        return None
    
    # En yüksek skorlu kategoriyi döndür
    best_category = max(scores, key=scores.get)
    print(f"🎯 Kategori tespit edildi: {best_category} (skor: {scores[best_category]})")
    return best_category


def get_relevant_knowledge(topic_name, subtopics=None):
    """
    Verilen konu için ilgili bilgi tabanı içeriğini döner.
    
    Args:
        topic_name: AI'nın tespit ettiği ana konu
        subtopics: AI'nın çıkardığı alt başlıklar
    
    Returns:
        Bilgi tabanı metni (string) veya boş string
    """
    category = detect_category(topic_name, subtopics)
    
    if not category:
        print(f"⚠️ '{topic_name}' için bilgi tabanı bulunamadı")
        return ''
    
    knowledge = KNOWLEDGE_MODULES.get(category, '')
    if knowledge:
        print(f"✅ Bilgi tabanından bilgi eklendi: {category} ({len(knowledge)} karakter)")
    
    return knowledge


def list_available_categories():
    """Mevcut kategorilerin listesini döner."""
    return list(KNOWLEDGE_MODULES.keys())