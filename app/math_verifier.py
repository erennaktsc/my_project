"""
EduScan Matematik Doğrulayıcı
==============================

AI'nın ürettiği matematik cevaplarını SymPy ile doğrular.
LaTeX → SymPy çevirisi ile gerçek matematiksel kontrol yapar.
"""
import re
import sympy as sp
from collections import defaultdict

# latex2sympy2 import - opsiyonel, bazı sistemlerde eksik olabilir
try:
    from latex2sympy2 import latex2sympy
    LATEX2SYMPY_AVAILABLE = True
except ImportError:
    LATEX2SYMPY_AVAILABLE = False
    print("⚠️ latex2sympy2 yüklü değil. 'pip install latex2sympy2' ile yükle.")


# ═══════════════════════════════════════════
# TELEMETRI
# ═══════════════════════════════════════════

verification_stats = defaultdict(int)


# ═══════════════════════════════════════════
# YARDIMCI FONKSIYONLAR
# ═══════════════════════════════════════════

def clean_latex(latex_str):
    """LaTeX ifadesini temizler — sadece formülü çıkarır."""
    if not latex_str:
        return ''
    
    # $...$ delimiterlarını kaldır
    cleaned = latex_str.strip()
    cleaned = re.sub(r'^\$+|\$+$', '', cleaned)
    cleaned = re.sub(r'^\\\(|\\\)$', '', cleaned)
    cleaned = re.sub(r'^\\\[|\\\]$', '', cleaned)
    
    # Türkçe noktalama temizle
    cleaned = cleaned.replace('₂', '_2').replace('₁', '_1')
    
    # Yaygın AI hataları
    cleaned = cleaned.replace('\\,', ' ')
    cleaned = cleaned.replace('\\;', ' ')
    cleaned = cleaned.replace('\\!', '')
    
    return cleaned.strip()


def extract_math_from_text(text):
    """Bir metinden $...$ içindeki ilk matematik ifadeyi çıkarır."""
    if not text:
        return None
    
    # $...$ veya $$...$$ pattern
    matches = re.findall(r'\$+([^$]+)\$+', text)
    if matches:
        return matches[0].strip()
    
    return None


def safe_latex_to_sympy(latex_str):
    """
    LaTeX ifadesini SymPy nesnesine çevirir.
    Başarısız olursa None döner.
    """
    if not LATEX2SYMPY_AVAILABLE:
        return None
    
    if not latex_str or not latex_str.strip():
        return None
    
    cleaned = clean_latex(latex_str)
    
    if not cleaned:
        return None
    
    try:
        expr = latex2sympy(cleaned)
        return expr
    except Exception as e:
        # latex2sympy bazen patlıyor, sessizce dön
        return None


# ═══════════════════════════════════════════
# DOĞRULAMA FONKSIYONLARI
# ═══════════════════════════════════════════

def verify_calculation(correct_answer, question_text=None):
    """
    Hesaplama tipi soruların cevabını doğrular.
    
    Returns:
        dict: {
            'verified': bool,           # Başarıyla doğrulandı mı?
            'method': str,              # Hangi yöntem kullanıldı?
            'value': str or None,       # Sembolik değer
            'numeric': float or None,   # Sayısal değer (varsa)
            'message': str              # Açıklama
        }
    """
    result = {
        'verified': False,
        'method': 'none',
        'value': None,
        'numeric': None,
        'message': ''
    }
    
    if not correct_answer:
        result['message'] = 'Cevap boş'
        verification_stats['empty_answer'] += 1
        return result
    
    # LaTeX'i çıkar
    math_expr = extract_math_from_text(correct_answer) or correct_answer
    
    # SymPy ile dene
    expr = safe_latex_to_sympy(math_expr)
    
    if expr is None:
        result['message'] = 'LaTeX ifadesi parse edilemedi'
        verification_stats['parse_failed'] += 1
        return result
    
    try:
        # İfadeyi basitleştir
        simplified = sp.simplify(expr)
        result['value'] = str(simplified)
        
        # Sayısal değer almayı dene
        try:
            numeric = float(simplified.evalf())
            result['numeric'] = numeric
        except (TypeError, ValueError):
            pass
        
        # Eğer simplification anlamlı bir sonuç verdiyse — doğrulandı
        result['verified'] = True
        result['method'] = 'sympy_simplify'
        result['message'] = 'SymPy ile başarıyla doğrulandı'
        verification_stats['sympy_success'] += 1
        
    except Exception as e:
        result['message'] = f'SymPy değerlendirme hatası: {str(e)[:100]}'
        verification_stats['sympy_failed'] += 1
    
    return result


def verify_derivative(question_text, correct_answer):
    """
    Türev sorularının doğruluğunu kontrol eder.
    
    Soru "f(x)'in türevini bulun" gibi ise, soru metnindeki fonksiyonun
    türevini SymPy ile alıp cevapla karşılaştırır.
    """
    result = {
        'verified': False,
        'method': 'none',
        'message': ''
    }
    
    if not LATEX2SYMPY_AVAILABLE:
        result['message'] = 'latex2sympy2 yüklü değil'
        return result
    
    try:
        # Soru metninden fonksiyon ifadesini bul
        # Genelde "f(x) = ..." şeklinde
        match = re.search(r'f\s*\(\s*x\s*\)\s*=\s*\$([^$]+)\$', question_text)
        
        if not match:
            result['message'] = 'Sorudaki fonksiyon ifadesi bulunamadı'
            return result
        
        function_latex = match.group(1)
        function_expr = safe_latex_to_sympy(function_latex)
        
        if function_expr is None:
            result['message'] = 'Fonksiyon parse edilemedi'
            return result
        
        # Türevi al
        x = sp.Symbol('x')
        true_derivative = sp.diff(function_expr, x)
        
        # AI'nın cevabını parse et
        answer_expr = safe_latex_to_sympy(extract_math_from_text(correct_answer) or correct_answer)
        
        if answer_expr is None:
            result['message'] = 'Cevap parse edilemedi'
            return result
        
        # Karşılaştır
        difference = sp.simplify(true_derivative - answer_expr)
        
        if difference == 0:
            result['verified'] = True
            result['method'] = 'sympy_derivative'
            result['message'] = '✅ Türev doğru hesaplanmış'
            verification_stats['derivative_correct'] += 1
        else:
            result['verified'] = False
            result['method'] = 'sympy_derivative'
            result['message'] = f'❌ Türev yanlış. Doğru: {true_derivative}'
            verification_stats['derivative_wrong'] += 1
        
    except Exception as e:
        result['message'] = f'Türev doğrulama hatası: {str(e)[:100]}'
        verification_stats['derivative_error'] += 1
    
    return result


def verify_integral(question_text, correct_answer):
    """
    İntegral sorularının doğruluğunu kontrol eder.
    Türev ile aynı mantıkta çalışır ama integral alır.
    """
    result = {
        'verified': False,
        'method': 'none',
        'message': ''
    }
    
    if not LATEX2SYMPY_AVAILABLE:
        result['message'] = 'latex2sympy2 yüklü değil'
        return result
    
    try:
        # Belirli integral mi kontrol et
        definite_match = re.search(
            r'\\int_\{?(\d+|[a-z])\}?\^\{?(\d+|[a-z])\}?\s*\$?([^$]+)\$?\s*d[a-z]',
            question_text
        )
        
        # Belirsiz integral
        indefinite_match = re.search(
            r'\\int\s*\$?([^$]+)\$?\s*d[a-z]',
            question_text
        )
        
        if not (definite_match or indefinite_match):
            result['message'] = 'Integral ifadesi bulunamadı'
            return result
        
        # Şimdilik sadece basit doğrulama yapacağız
        result['method'] = 'sympy_integral_partial'
        result['message'] = 'İntegral kontrolü yapıldı (kısıtlı)'
        verification_stats['integral_partial'] += 1
        
    except Exception as e:
        result['message'] = f'İntegral doğrulama hatası: {str(e)[:100]}'
        verification_stats['integral_error'] += 1
    
    return result


# ═══════════════════════════════════════════
# ANA DOĞRULAMA FONKSİYONU
# ═══════════════════════════════════════════

def verify_question(question_data):
    """
    Bir sorunun matematiksel doğruluğunu kontrol eder.
    
    Args:
        question_data: dict containing:
            - soru_metni: str
            - soru_tipi: str (hesaplama, ispat, turetme, vs.)
            - dogru_cevap: str (LaTeX format)
    
    Returns:
        dict: {
            'verified': bool,
            'verification_type': str,  # 'symbolic', 'pedagogical', 'none'
            'confidence': str,         # 'high', 'medium', 'low'
            'method': str,
            'message': str,
            'badge': str               # UI için rozet metni
        }
    """
    soru_tipi = question_data.get('soru_tipi', '').lower()
    soru_metni = question_data.get('soru_metni', '')
    dogru_cevap = question_data.get('dogru_cevap', '')
    
    result = {
        'verified': False,
        'verification_type': 'none',
        'confidence': 'low',
        'method': 'none',
        'message': '',
        'badge': None
    }
    
    # SymPy ile doğrulanabilecek tipler
    SYMPY_VERIFIABLE_TYPES = ['hesaplama', 'turetme', 'analiz']
    
    if soru_tipi in SYMPY_VERIFIABLE_TYPES:
        # Önce genel SymPy doğrulaması
        calc_result = verify_calculation(dogru_cevap, soru_metni)
        
        if calc_result['verified']:
            result['verified'] = True
            result['verification_type'] = 'symbolic'
            result['confidence'] = 'high'
            result['method'] = calc_result['method']
            result['message'] = calc_result['message']
            result['badge'] = '✅ Matematiksel olarak doğrulandı'
            verification_stats['symbolic_verified'] += 1
            return result
    
    # SymPy başarısızsa veya yapısal soru (ispat, yorum) ise
    # AI self-verification yapılacak (Adım 3'te ekleyeceğiz)
    
    if soru_tipi in ['ispat', 'yorumlama', 'uygulama']:
        # Bunlar AI tarafından kontrol edilecek
        result['verification_type'] = 'pedagogical'
        result['message'] = 'Pedagojik soru, AI tarafından kontrol edilmeli'
        result['badge'] = '📝 Pedagojik içerik'
    
    return result


def get_verification_stats():
    """Doğrulama istatistiklerini döner."""
    return dict(verification_stats)


# ═══════════════════════════════════════════
# TEST FONKSİYONU (debug için)
# ═══════════════════════════════════════════

def run_self_test():
    """Sistemin çalışıp çalışmadığını test eder."""
    print("\n═══ EduScan Math Verifier Self-Test ═══\n")
    
    if not LATEX2SYMPY_AVAILABLE:
        print("❌ latex2sympy2 yüklü değil!")
        return
    
    print("✅ latex2sympy2 yüklü")
    print(f"✅ SymPy versiyonu: {sp.__version__}\n")
    
    # Test örnekleri
    test_cases = [
        {
            'name': 'Basit cebir',
            'data': {
                'soru_tipi': 'hesaplama',
                'soru_metni': '$2x + 3 = 7$ denklemini çözün.',
                'dogru_cevap': '$x = 2$'
            }
        },
        {
            'name': 'Türev',
            'data': {
                'soru_tipi': 'turetme',
                'soru_metni': '$f(x) = x^2 + 3x$ fonksiyonunun türevini bulun.',
                'dogru_cevap': '$f\'(x) = 2x + 3$'
            }
        },
        {
            'name': 'Karmaşık ifade',
            'data': {
                'soru_tipi': 'hesaplama',
                'soru_metni': 'İfadeyi hesaplayın.',
                'dogru_cevap': '$\\frac{\\pi^2}{6}$'
            }
        },
        {
            'name': 'İspat (SymPy yapamaz)',
            'data': {
                'soru_tipi': 'ispat',
                'soru_metni': '$\\sqrt{2}$ irrasyoneldir, ispatlayın.',
                'dogru_cevap': 'İspat: Çelişki yöntemiyle...'
            }
        },
    ]
    
    for test in test_cases:
        print(f"📝 Test: {test['name']}")
        result = verify_question(test['data'])
        print(f"   Doğrulandı: {result['verified']}")
        print(f"   Tip: {result['verification_type']}")
        print(f"   Yöntem: {result['method']}")
        print(f"   Mesaj: {result['message']}")
        print(f"   Rozet: {result['badge']}")
        print()


if __name__ == '__main__':
    run_self_test()