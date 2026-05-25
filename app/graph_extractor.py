"""
EduScan Grafik Çıkarıcı
========================

AI'nın boş gönderdiği graph_data alanını, soru metninden otomatik üretir.
Pattern matching ve regex ile fonksiyonları ve grafik tiplerini tespit eder.
"""
import re
from typing import Optional


# ═══════════════════════════════════════════
# YARDIMCI: Fonksiyonu Soru Metninden Çıkar
# ═══════════════════════════════════════════

def extract_function(text: str) -> Optional[str]:
    """
    Soru metninden f(x) = ... formatında fonksiyon çıkarır.
    
    Örnekler:
    - "f(x) = x² + 3x" → "x**2 + 3*x"
    - "y = sin(x)" → "sin(x)"
    - "g(x)=2x-1" → "2*x - 1"
    """
    if not text:
        return None
    
    # Yaygın patternler — sıralı, en spesifikten genele
    patterns = [
        r'f\s*\(\s*x\s*\)\s*=\s*([^.,;\n\$]+)',
        r'y\s*=\s*([^.,;\n\$]+)',
        r'g\s*\(\s*x\s*\)\s*=\s*([^.,;\n\$]+)',
        r'h\s*\(\s*x\s*\)\s*=\s*([^.,;\n\$]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            expr = match.group(1).strip()
            # LaTeX temizleme
            expr = clean_math_expression(expr)
            if is_valid_expression(expr):
                return expr
    
    return None


def clean_math_expression(expr: str) -> str:
    """Matematik ifadesini temizler ve Python syntax'ına çevirir."""
    # LaTeX komutlarını temizle
    expr = expr.replace('\\', '')
    expr = re.sub(r'\$+', '', expr)  # $ işaretleri
    expr = re.sub(r'\{|\}', '', expr)  # { } parantezler
    
    # Türkçe karakterler
    expr = expr.replace('π', 'pi')
    expr = expr.replace('²', '**2')
    expr = expr.replace('³', '**3')
    expr = expr.replace('⁴', '**4')
    expr = expr.replace('×', '*')
    expr = expr.replace('·', '*')
    
    # x^2 → x**2
    expr = re.sub(r'\^(\d+)', r'**\1', expr)
    expr = re.sub(r'\^\(([^)]+)\)', r'**(\1)', expr)
    
    # 2x → 2*x (sayı + harf)
    expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)
    
    # )( → )*(
    expr = expr.replace(')(', ')*(')
    
    # Aşırı boşlukları temizle
    expr = re.sub(r'\s+', ' ', expr).strip()
    
    return expr


def is_valid_expression(expr: str) -> bool:
    """İfadenin geçerli bir matematik ifadesi olup olmadığını kontrol eder."""
    if not expr or len(expr) < 1:
        return False
    
    # En az bir x içermeli (fonksiyon olduğu için)
    if 'x' not in expr.lower():
        return False
    
    # Aşırı uzunsa muhtemelen yanlış parse edilmiş
    if len(expr) > 100:
        return False
    
    # Türkçe metin içermesin
    turkce_kelimeler = ['ve', 'için', 'olan', 'bulun', 'hesapla', 'göster', 'yazın']
    for kelime in turkce_kelimeler:
        if kelime in expr.lower():
            return False
    
    return True


# ═══════════════════════════════════════════
# YARDIMCI: Aralık Çıkar [a, b]
# ═══════════════════════════════════════════

def extract_range(text: str) -> Optional[list]:
    """
    Soru metninden [a, b] aralığını çıkarır.
    
    Örnekler:
    - "[0, 2]" → [0, 2]
    - "[-1, 3]" → [-1, 3]
    - "0 ≤ x ≤ 2" → [0, 2]
    - "[0,π]" → [0, 3.14159]
    """
    if not text:
        return None
    
    # Pattern 1: [a, b] veya [a,b]
    match = re.search(r'\[\s*(-?[\d./]+|pi|π|-pi|-π)\s*,\s*(-?[\d./]+|pi|π|-pi|-π)\s*\]', text, re.IGNORECASE)
    if match:
        a = parse_number(match.group(1))
        b = parse_number(match.group(2))
        if a is not None and b is not None:
            return [a, b]
    
    # Pattern 2: a ≤ x ≤ b
    match = re.search(r'(-?[\d./]+)\s*[≤<]\s*x\s*[≤<]\s*(-?[\d./]+)', text)
    if match:
        a = parse_number(match.group(1))
        b = parse_number(match.group(2))
        if a is not None and b is not None:
            return [a, b]
    
    return None


def parse_number(s: str) -> Optional[float]:
    """String'i sayıya çevirir. 'pi' gibi sabitleri de destekler."""
    if not s:
        return None
    
    s = s.strip().lower()
    
    if s in ('pi', 'π'):
        return 3.14159265
    if s in ('-pi', '-π'):
        return -3.14159265
    if s in ('2pi', '2π'):
        return 6.28318530
    
    try:
        if '/' in s:
            parts = s.split('/')
            return float(parts[0]) / float(parts[1])
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


# ═══════════════════════════════════════════
# YARDIMCI: Nokta Çıkar (x=a)
# ═══════════════════════════════════════════

def extract_point(text: str) -> Optional[float]:
    """
    Soru metninden bir nokta değeri çıkarır.
    
    Örnekler:
    - "x = 2 noktasında" → 2
    - "x=-1" → -1
    """
    if not text:
        return None
    
    match = re.search(r'x\s*=\s*(-?[\d./]+|pi|π)', text, re.IGNORECASE)
    if match:
        return parse_number(match.group(1))
    
    return None


# ═══════════════════════════════════════════
# ANA TESPIT FONKSIYONU
# ═══════════════════════════════════════════

def detect_graph_type(soru_metni: str, soru_tipi: str = '') -> Optional[str]:
    """
    Soru metnine bakarak grafik tipini tespit eder.
    
    Returns: 'function', 'integral', 'derivative', 'critical_points' veya None
    """
    if not soru_metni:
        return None
    
    metin = soru_metni.lower()
    
    # İntegral göstergeleri
    integral_keywords = [
        'belirli integral', 'integral hesapla', 'integralin değer',
        'alan altında', 'altındaki alan', 'arasındaki alan',
        'eğri altında', '∫', 'riemann toplam'
    ]
    if any(kw in metin for kw in integral_keywords):
        # Eğer aralık [a,b] de varsa, kesin integral
        if extract_range(soru_metni):
            return 'integral'
    
    # Türev / Teğet göstergeleri
    derivative_keywords = [
        'teğet doğru', 'teğet denklem', 'teğet çiz',
        'lineer yaklaşım', 'noktasında türev',
        'türev kullanarak yaklaşık'
    ]
    if any(kw in metin for kw in derivative_keywords):
        if extract_point(soru_metni) is not None:
            return 'derivative'
    
    # Kritik nokta göstergeleri
    critical_keywords = [
        'kritik nokta', 'yerel maksimum', 'yerel minimum',
        'yerel ekstremum', 'maksimum ve minimum',
        'monotonluk', 'artan ve azalan'
    ]
    if any(kw in metin for kw in critical_keywords):
        return 'critical_points'
    
    # Fonksiyon grafiği göstergeleri
    function_keywords = [
        'grafiğini çiz', 'grafiğini gösteri',
        'fonksiyonun grafik', 'eğriyi çiz',
        'kesişim nokta', 'kesişen noktalar'
    ]
    if any(kw in metin for kw in function_keywords):
        return 'function'
    
    return None


def auto_generate_graph_data(soru: dict) -> Optional[dict]:
    """
    Soru objesinden otomatik graph_data üretir.
    AI boş veya yanlış veri gönderirse bu kullanılır.
    """
    soru_metni = soru.get('soru_metni', '')
    soru_tipi = soru.get('soru_tipi', '')
    
    # Grafik tipini tespit et
    graph_type = detect_graph_type(soru_metni, soru_tipi)
    if not graph_type:
        return None
    
    # Fonksiyonu çıkar
    function = extract_function(soru_metni)
    if not function:
        return None  # Fonksiyon yoksa grafik üretemeyiz
    
    # Tipine göre uygun yapıyı oluştur
    if graph_type == 'integral':
        int_range = extract_range(soru_metni) or [0, 1]
        x_padding = max(0.5, (int_range[1] - int_range[0]) * 0.2)
        
        return {
            'graph_type': 'integral',
            'function': function,
            'integral_range': int_range,
            'x_range': [int_range[0] - x_padding, int_range[1] + x_padding],
            'title': f'∫ f(x) dx — [{int_range[0]}, {int_range[1]}]'
        }
    
    elif graph_type == 'derivative':
        point = extract_point(soru_metni) or 1
        x_range = [point - 3, point + 3]
        
        # Türev otomatik hesaplanamıyor, sadece fonksiyonu çizelim
        return {
            'graph_type': 'function',
            'functions': [{'expr': function, 'label': f'f(x) = {function.replace("**", "^")}'}],
            'x_range': x_range,
            'title': f'x={point} Noktasında Davranış',
            'annotations': [{'x': point, 'y': None, 'text': f'x={point}'}]
        }
    
    elif graph_type == 'critical_points':
        x_range = [-5, 5]
        # Fonksiyona göre aralık ayarla
        if 'x**3' in function or 'x**4' in function:
            x_range = [-3, 3]
        elif 'sin' in function or 'cos' in function:
            x_range = [-6.28, 6.28]
        
        return {
            'graph_type': 'function',
            'functions': [{'expr': function, 'label': f'f(x) = {function.replace("**", "^")}'}],
            'x_range': x_range,
            'title': 'Kritik Noktalar'
        }
    
    elif graph_type == 'function':
        x_range = [-5, 5]
        if 'sin' in function or 'cos' in function:
            x_range = [-6.28, 6.28]
        elif 'log' in function or 'ln' in function:
            x_range = [0.1, 10]
        elif 'exp' in function:
            x_range = [-3, 3]
        
        return {
            'graph_type': 'function',
            'functions': [{'expr': function, 'label': f'f(x) = {function.replace("**", "^")}'}],
            'x_range': x_range,
            'title': 'Fonksiyon Grafiği'
        }
    
    return None


# ═══════════════════════════════════════════
# SELF TEST
# ═══════════════════════════════════════════

def run_self_test():
    """Modülü test eder."""
    print("\n═══ EduScan Graph Extractor Self-Test ═══\n")
    
    tests = [
        {
            'soru_metni': 'f(x) = x² fonksiyonunun [0, 2] aralığındaki belirli integralini hesaplayın.',
            'beklenen_tip': 'integral'
        },
        {
            'soru_metni': 'f(x) = x³ - 3x fonksiyonunun yerel maksimum ve minimum noktalarını bulun.',
            'beklenen_tip': 'critical_points'
        },
        {
            'soru_metni': 'f(x) = sin(x) fonksiyonunun x = π/2 noktasında teğet doğrusunu yazın.',
            'beklenen_tip': 'derivative'
        },
        {
            'soru_metni': 'f(x) = 2x + 1 ve g(x) = x² fonksiyonlarının kesişim noktalarını bulun.',
            'beklenen_tip': 'function'
        },
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"📊 Test {i}: {test['soru_metni'][:60]}...")
        
        # Tip tespit
        tip = detect_graph_type(test['soru_metni'])
        print(f"   Beklenen tip: {test['beklenen_tip']}, Bulunan: {tip}")
        
        # Fonksiyon çıkar
        func = extract_function(test['soru_metni'])
        print(f"   Fonksiyon: {func}")
        
        # Aralık (varsa)
        rng = extract_range(test['soru_metni'])
        if rng:
            print(f"   Aralık: {rng}")
        
        # Tam graph_data
        gd = auto_generate_graph_data({'soru_metni': test['soru_metni']})
        if gd:
            print(f"   ✅ graph_data üretildi: {gd['graph_type']}")
        else:
            print(f"   ❌ graph_data üretilemedi")
        
        print()


if __name__ == '__main__':
    run_self_test()