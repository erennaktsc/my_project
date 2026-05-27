"""
EduScan AI Service — Gemini API entegrasyonu
3 katmanlı savunma sistemi ile sağlam soru üretimi
"""
import os
import re
import json
import time
import logging
from collections import defaultdict
from PIL import Image
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════


ANALYSIS_MODEL = 'gemini-2.5-flash'      # Çalışan, kararlı model
GENERATION_MODEL = 'gemini-2.5-flash'    # Çalışan, kararlı model
# ═══════════════════════════════════════════
# JSON SCHEMAS — Structured Output için
# ═══════════════════════════════════════════

# Doküman analiz şeması
ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["konu", "ozet", "anahtar_kavramlar", "alt_basliklar",
                 "on_gereksinimler", "tipik_hatalar", "icerik_tipi", 
                 "zorluk_seviyesi", "ham_metin"],
    "properties": {
        "konu": {
            "type": "string",
            "description": "Ana konunun spesifik akademik adı"
        },
        "ozet": {
            "type": "string",
            "description": "Konunun matematiksel/teorik özü (3-4 cümle)"
        },
        "anahtar_kavramlar": {
            "type": "array",
            "items": {"type": "string"},
            "description": "En önemli 5-7 spesifik kavram"
        },
        "alt_basliklar": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Konunun alt başlıkları"
        },
        "on_gereksinimler": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Önceden bilinmesi gereken konular"
        },
        "tipik_hatalar": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Öğrencilerin yaptığı yaygın hatalar"
        },
        "icerik_tipi": {
            "type": "string",
            "enum": ["konu_anlatimi", "soru", "karisik"]
        },
        "zorluk_seviyesi": {
            "type": "string",
            "enum": ["lise", "universite_1", "universite_2_3", "ileri"]
        },
        "ham_metin": {
            "type": "string",
            "description": "Dökümandaki ana metnin özeti (max 1500 kelime)"
        }
    }
}


# Soru şeması (bir soru için)
QUESTION_SCHEMA_BASE = {
    "type": "object",
    "required": ["soru_metni", "soru_tipi", "zorluk", "olculen_kavram",
             "cozum_adimlari", "dogru_cevap", "ipucu",
             "bloom_seviyesi",
             "has_graph", "graph_description"],
    "properties": {
        "soru_metni": {"type": "string"},
        "soru_tipi": {
            "type": "string",
            "enum": ["hesaplama", "ispat", "turetme", "analiz", "yorumlama", "uygulama"]
        },
        "zorluk": {
            "type": "string",
            "enum": ["kolay", "orta", "zor"]
        },
        "olculen_kavram": {"type": "string"},
        "secenekler": {
            "type": "array",
            "items": {"type": "string"}
        },
        "cozum_adimlari": {
            "type": "array",
            "items": {"type": "string"}
        },
        "dogru_cevap": {"type": "string"},
        "ipucu": {"type": "string"},
        "bloom_seviyesi": {  # YENİ
            "type": "string",
            "enum": ["hatirlama", "anlama", "uygulama", "analiz", "degerlendirme", "yaratma"]
        },
        "has_graph": {"type": "boolean"},
        "graph_description": {"type": "string"},
        "graph_data": {
            "type": "object",
            "description": "Matplotlib için yapısal grafik verisi"
        }
    }
}

# Kaynak referansı içeren soru şeması (PDF'ler için)
QUESTION_SCHEMA_WITH_SOURCE = {
    "type": "object",
    "required": QUESTION_SCHEMA_BASE["required"] + 
                ["kaynak_sayfa", "kaynak_aciklama"],
    "properties": {
        **QUESTION_SCHEMA_BASE["properties"],
        "kaynak_sayfa": {"type": "integer"},
        "kaynak_aciklama": {"type": "string"}
    }
}


def get_questions_schema(has_pages=False):
    """Soru üretimi için top-level şema döner."""
    item_schema = QUESTION_SCHEMA_WITH_SOURCE if has_pages else QUESTION_SCHEMA_BASE
    return {
        "type": "object",
        "required": ["sorular"],
        "properties": {
            "sorular": {
                "type": "array",
                "items": item_schema
            }
        }
    }

# Logging ayarla
logger = logging.getLogger('eduscan.ai')
logger.setLevel(logging.INFO)

# Telemetri — hangi hatanın kaç kez geldiğini sayar
error_stats = defaultdict(int)
success_stats = defaultdict(int)


# ═══════════════════════════════════════════
# HATA KATEGORİZASYONU
# ═══════════════════════════════════════════

class ErrorCategory:
    """Gemini hatalarını kategorize eder."""
    OVERLOAD = "overload"           # 503, UNAVAILABLE - sunucu yoğun
    RATE_LIMIT = "rate_limit"       # 429 - rate limit aşıldı
    UPLOAD_TERMINATED = "upload"    # 400 - upload sorunu
    JSON_PARSE = "json_parse"       # JSON parse hatası
    QUOTA = "quota"                 # API quota bitti
    AUTH = "auth"                   # API key sorunu
    NETWORK = "network"             # Bağlantı sorunu
    UNKNOWN = "unknown"
    # ═══════════════════════════════════════════
# KULLANICI DOSTU HATA MESAJLARI
# ═══════════════════════════════════════════

USER_FRIENDLY_MESSAGES = {
    ErrorCategory.OVERLOAD: {
        "title": "Yapay Zeka Yoğun",
        "message": "Yapay zeka sunucuları şu an çok yoğun. Lütfen 1-2 dakika sonra tekrar deneyin.",
        "icon": "⏳",
        "action": "Tekrar Dene"
    },
    ErrorCategory.RATE_LIMIT: {
        "title": "Çok Fazla İstek",
        "message": "Kısa sürede çok fazla istek gönderildi. Lütfen 1-2 dakika bekleyip tekrar deneyin.",
        "icon": "🚦",
        "action": "Tekrar Dene"
    },
    ErrorCategory.UPLOAD_TERMINATED: {
        "title": "Dosya Yüklenemedi",
        "message": "Dosya yüklenirken bir sorun oluştu. Bu genelde geçicidir, lütfen tekrar deneyin.",
        "icon": "📤",
        "action": "Tekrar Dene"
    },
    ErrorCategory.JSON_PARSE: {
        "title": "Dosya Çok Karmaşık",
        "message": "Dökümandaki içerik beklenenden karmaşık. Daha küçük bir bölümle veya tek sayfa ile deneyin.",
        "icon": "📄",
        "action": "Yeni Dosya Yükle"
    },
    ErrorCategory.QUOTA: {
        "title": "Günlük Limit Aşıldı",
        "message": "Sistemin günlük kullanım limiti aşıldı. Lütfen yarın tekrar deneyin veya yöneticiye bildirin.",
        "icon": "🚫",
        "action": "Ana Sayfaya Dön"
    },
    ErrorCategory.AUTH: {
        "title": "Sistem Yapılandırma Hatası",
        "message": "Sistemde teknik bir yapılandırma sorunu var. Bu hata bizim ekibimize bildirildi.",
        "icon": "🔧",
        "action": "Ana Sayfaya Dön"
    },
    ErrorCategory.NETWORK: {
        "title": "Bağlantı Sorunu",
        "message": "İnternet bağlantısında bir sorun oluştu. Bağlantınızı kontrol edip tekrar deneyin.",
        "icon": "🌐",
        "action": "Tekrar Dene"
    },
    ErrorCategory.UNKNOWN: {
        "title": "Beklenmedik Bir Sorun",
        "message": "Beklenmedik bir hata oluştu. Lütfen tekrar deneyin. Sorun devam ederse farklı bir dosya deneyin.",
        "icon": "⚠️",
        "action": "Tekrar Dene"
    }
}


def get_friendly_error(error):
    """
    Teknik hatayı kullanıcı dostu mesaja çevirir.
    Frontend'e gönderilecek dict döner.
    
    Returns:
        dict: {title, message, icon, action, category, technical_details}
    """
    category = categorize_error(error)
    friendly = USER_FRIENDLY_MESSAGES.get(category, USER_FRIENDLY_MESSAGES[ErrorCategory.UNKNOWN])
    
    return {
        **friendly,
        "category": category,
        "technical_details": str(error)[:200]  # Debug için kısa teknik detay
    }


def categorize_error(error):
    """Bir hatayı kategorize eder ve hangi tip olduğunu döner."""
    error_str = str(error).lower()
    
    if 'upload' in error_str and 'terminated' in error_str:
        return ErrorCategory.UPLOAD_TERMINATED
    if '503' in error_str or 'unavailable' in error_str or 'overloaded' in error_str:
        return ErrorCategory.OVERLOAD
    if '429' in error_str or 'rate limit' in error_str:
        return ErrorCategory.RATE_LIMIT
    if 'quota' in error_str or 'exceeded' in error_str:
        return ErrorCategory.QUOTA
    if 'api key' in error_str or 'authentication' in error_str or '401' in error_str:
        return ErrorCategory.AUTH
    if 'connection' in error_str or 'timeout' in error_str or 'network' in error_str:
        return ErrorCategory.NETWORK
    if 'json' in error_str or 'decode' in error_str:
        return ErrorCategory.JSON_PARSE
    return ErrorCategory.UNKNOWN


def get_retry_delay(category, attempt):
    """Hata kategorisine göre bekleme süresi döner (saniye)."""
    base_delays = {
        ErrorCategory.OVERLOAD: 5,
        ErrorCategory.RATE_LIMIT: 30,      # Rate limit için uzun bekleme
        ErrorCategory.UPLOAD_TERMINATED: 3, # Upload sorunu için kısa bekleme
        ErrorCategory.NETWORK: 5,
        ErrorCategory.UNKNOWN: 5,
    }
    base = base_delays.get(category, 5)
    # Exponential backoff with cap
    return min(base * (1.5 ** attempt), 60)


# ═══════════════════════════════════════════
# AKILLI RETRY MEKANİZMASI
# ═══════════════════════════════════════════

def call_with_retry(func, max_retries=8, context="API call"):
    """
    Hata tipine göre akıllı retry yapar.
    AUTH ve QUOTA hatalarında retry yapmaz (anlamsız).
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = func()
            # Başarılı çağrı — telemetri güncelle
            success_stats[context] += 1
            if attempt > 0:
                logger.info(f"✅ {context} {attempt + 1}. denemede başarılı")
            return result
        
        except Exception as e:
            last_error = e
            category = categorize_error(e)
            error_stats[category] += 1
            
            # AUTH ve QUOTA hatalarında retry yapma
            if category in (ErrorCategory.AUTH, ErrorCategory.QUOTA):
                logger.error(f"❌ {context}: {category} hatası, retry yapılmıyor: {e}")
                raise
            
            # Son deneme ise hatayı fırlat
            if attempt == max_retries - 1:
                logger.error(f"❌ {context}: {max_retries} deneme sonrası başarısız: {e}")
                raise
            
            # Beklemeden devam et
            delay = get_retry_delay(category, attempt)
            logger.warning(
                f"⚠️ {context} hata ({category}): deneme {attempt + 1}/{max_retries}. "
                f"{delay:.1f}sn bekleniyor..."
            )
            print(
                f"⚠️ {context}: {category} hatası "
                f"(deneme {attempt + 1}/{max_retries}). {delay:.1f}sn bekleniyor..."
            )
            time.sleep(delay)
    
    # Buraya gelmemeli ama yine de
    raise last_error


# ═══════════════════════════════════════════
# JSON PARSE — 4 KATMANLI
# ═══════════════════════════════════════════

def clean_json_response(text):
    """Markdown kod bloklarını temizler."""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    return text.strip()


def parse_json_response(text):
    """
    JSON metnini Python sözlüğüne çevirir.
    4 katmanlı agresif onarım yapar (LaTeX backslash sorunları için).
    """
    cleaned = clean_json_response(text)
    
    # Katman 1: Doğrudan parse
    try:
        result = json.loads(cleaned)
        success_stats["json_parse_direct"] += 1  # YENİ — telemetri
        return result
    except json.JSONDecodeError:
        pass
    
    # Katman 2: Karakter karakter escape onarımı
    try:
        result = []
        i = 0
        n = len(cleaned)
        in_string = False
        
        while i < n:
            ch = cleaned[i]
            if ch == '"' and (i == 0 or cleaned[i-1] != '\\'):
                in_string = not in_string
            
            if in_string and ch == '\\' and i + 1 < n:
                next_char = cleaned[i+1]
                if next_char in '"\\/bfnrt':
                    result.append(ch)
                    result.append(next_char)
                    i += 2
                    continue
                elif next_char == 'u' and i + 5 < n:
                    result.append(cleaned[i:i+6])
                    i += 6
                    continue
                else:
                    result.append('\\\\')
                    result.append(next_char)
                    i += 2
                    continue
            
            result.append(ch)
            i += 1
        
        fixed = ''.join(result)
        parsed = json.loads(fixed)
        success_stats["json_parse_layer2"] += 1  # YENİ
        return parsed
    except json.JSONDecodeError:
        pass
    
    # Katman 3: strict=False
    try:
        result = json.loads(cleaned, strict=False)
        success_stats["json_parse_layer3"] += 1  # YENİ
        return result
    except json.JSONDecodeError:
        pass
    
    try:
        # Önce zaten doğru olanları geçici karakterlerle koru
        temp = cleaned.replace('\\\\', '\x00')
        temp = temp.replace('\\"', '\x01')
        temp = temp.replace('\\n', '\x02')
        temp = temp.replace('\\t', '\x03')
        temp = temp.replace('\\r', '\x04')
        temp = temp.replace('\\/', '\x05')
        temp = temp.replace('\\b', '\x06')
        temp = temp.replace('\\f', '\x07')
        
        # Kalan tüm \ → \\
        temp = temp.replace('\\', '\\\\')
        
        # Geçici karakterleri geri al
        temp = temp.replace('\x00', '\\\\')
        temp = temp.replace('\x01', '\\"')
        temp = temp.replace('\x02', '\\n')
        temp = temp.replace('\x03', '\\t')
        temp = temp.replace('\x04', '\\r')
        temp = temp.replace('\x05', '\\/')
        temp = temp.replace('\x06', '\\b')
        temp = temp.replace('\x07', '\\f')
        
        result = json.loads(temp)
        success_stats["json_parse_layer4"] += 1
        return result
    except json.JSONDecodeError as e:
        # Son çare: telemetri kaydet ve hatayı fırlat
        error_stats[ErrorCategory.JSON_PARSE] += 1
        logger.error(f"JSON parse 4 katmanda başarısız: char {e.pos}")
        print(f"\n⚠️ JSON parse hatası char {e.pos}'da")
        print(f"Problemli civar: ...{cleaned[max(0,e.pos-50):e.pos+50]}...")
        print(f"\nHam metin başlangıcı (ilk 500):\n{cleaned[:500]}")
        raise


# ═══════════════════════════════════════════
# 3 KATMANLI DOSYA GÖNDERİM SİSTEMİ
# ═══════════════════════════════════════════

def _try_inline_base64(image_path, file_ext, prompt, model, config=None):
    """Katman 1: Inline base64 — en güvenilir yöntem (20MB altı)."""
    logger.info(f"🛡️ Katman 1: Inline base64 deneniyor ({file_ext})")
    
    kwargs = {"model": model}
    if config:
        kwargs["config"] = config
    
    if file_ext == 'pdf':
        with open(image_path, 'rb') as f:
            pdf_bytes = f.read()
        
        kwargs["contents"] = [
            types.Part.from_bytes(
                data=pdf_bytes,
                mime_type='application/pdf'
            ),
            prompt
        ]
        return client.models.generate_content(**kwargs)
    else:
        with Image.open(image_path) as image:
            image_copy = image.copy()
        
        kwargs["contents"] = [prompt, image_copy]
        return client.models.generate_content(**kwargs)


def _try_files_upload(image_path, file_ext, prompt, model, config=None):
    """Katman 2: Files Upload API (büyük dosyalar için yedek)."""
    logger.info(f"🛡️ Katman 2: Files Upload deneniyor ({file_ext})")
    
    uploaded_file = client.files.upload(file=image_path)
    try:
        kwargs = {
            "model": model,
            "contents": [prompt, uploaded_file]
        }
        if config:
            kwargs["config"] = config
        
        return client.models.generate_content(**kwargs)
    finally:
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass


def _send_to_gemini(image_path, prompt, model, config=None):
    """
    3 katmanlı savunma sistemi ile dosyayı Gemini'ye gönderir.
    
    Args:
        image_path: Dosya yolu
        prompt: Gemini'ye verilecek prompt
        model: Kullanılacak model adı
        config: Structured output için config (response_schema vb.)
    """
    file_ext = image_path.lower().split('.')[-1]
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    
    logger.info(f"📤 Dosya gönderiliyor: {os.path.basename(image_path)} ({file_size_mb:.1f}MB)")
    
    # Katman 1: Inline base64 (20MB altı için)
    if file_size_mb < 19:
        try:
            return call_with_retry(
                lambda: _try_inline_base64(image_path, file_ext, prompt, model, config),
                max_retries=5,
                context="inline_base64"
            )
        except Exception as e:
            category = categorize_error(e)
            logger.warning(f"⚠️ Katman 1 başarısız ({category}): {e}")
            
            if category not in (ErrorCategory.UPLOAD_TERMINATED, ErrorCategory.NETWORK, ErrorCategory.UNKNOWN):
                raise
            
            print(f"\n🔄 Katman 1 ({category}) başarısız, Katman 2'ye geçiliyor...")
    
    # Katman 2: Files Upload
    return call_with_retry(
        lambda: _try_files_upload(image_path, file_ext, prompt, model, config),
        max_retries=5,
        context="files_upload"
    )


# ═══════════════════════════════════════════
# ANALYZE DOCUMENT
# ═══════════════════════════════════════════

def analyze_document(image_path):
    """Görüntüyü veya PDF'i analiz eder. Structured output kullanır."""
    
    prompt = """Sen deneyimli bir akademik içerik analisti ve sınav danışmanısın. 
Bu görüntü/PDF bir ders materyalidir. Görevin sadece "ne yazıyor" demek değil, 
derinlemesine bir konu profili çıkarmaktır.

Şu bilgileri derinlemesine analiz et:

- "konu": Ana konunun SPESİFİK akademik adı (örn: "Parçalı Fonksiyonlarda Süreklilik", sadece "Fonksiyonlar" değil)
- "ozet": Konunun matematiksel/teorik özü (3-4 cümle)
- "anahtar_kavramlar": En önemli 5-7 spesifik kavram
- "alt_basliklar": Konunun alt başlıkları, 3-5 tane
- "on_gereksinimler": Bu konuyu anlamak için bilinmesi gereken konular
- "tipik_hatalar": Öğrencilerin bu konuda yaptığı yaygın hatalar (2-3 tane)
- "icerik_tipi": konu_anlatimi, soru veya karisik
- "zorluk_seviyesi": lise, universite_1, universite_2_3 veya ileri
- "ham_metin": Dökümandaki ana metnin ÖZET'i (max 1500 kelime). Matematik formülleri $ ile sarılmış LaTeX formatında."""

    # Structured output config — JSON schema ile garantili JSON dönüş
    config = {
        'response_mime_type': 'application/json',
        'response_schema': ANALYSIS_SCHEMA
    }
    
    response = _send_to_gemini(image_path, prompt, ANALYSIS_MODEL, config=config)
    return response.text


# ═══════════════════════════════════════════
# GENERATE QUESTIONS
# ═══════════════════════════════════════════

def generate_questions(topic_data, num_questions=3, has_pages=False, bloom_levels=None):
    """
    Konuya göre üniversite seviyesi akademik açık uçlu sorular üretir.
    
    Args:
        bloom_levels: Liste, üretilecek Bloom seviyeleri.
                      None ise karışık (varsayılan davranış)
                      Örn: ['analiz', 'degerlendirme', 'yaratma']
    """
    
    alt_basliklar = topic_data.get('alt_basliklar', [])
    on_gereksinimler = topic_data.get('on_gereksinimler', [])
    tipik_hatalar = topic_data.get('tipik_hatalar', [])
    total_pages = topic_data.get('total_pages', 1)
    # ═══ Bloom Taksonomisi bölümü ═══
    bloom_section = ""
    if bloom_levels and isinstance(bloom_levels, list) and len(bloom_levels) > 0:
        bloom_descriptions = {
            'hatirlama': 'Hatırlama (tanımlama, listeleme, isimlendirme)',
            'anlama': 'Anlama (açıklama, özetleme, yorumlama, sınıflandırma)',
            'uygulama': 'Uygulama (hesaplama, çözme, kullanma, gösterme)',
            'analiz': 'Analiz (karşılaştırma, ayrıştırma, ilişki kurma, organizasyon)',
            'degerlendirme': 'Değerlendirme (eleştirme, doğrulama, yargılama, savunma)',
            'yaratma': 'Yaratma (tasarlama, üretme, planlama, hipotez kurma)'
        }
        
        selected = [bloom_descriptions.get(level, level) for level in bloom_levels]
        bloom_section = f"""

═══ BLOOM TAKSONOMİSİ FİLTRESİ — KRİTİK ═══

⚠️ Sorular SADECE şu Bloom seviyelerinde olmalı:
{chr(10).join(f'  • {desc}' for desc in selected)}

Her soru için "bloom_seviyesi" alanını DOLDUR:
- hatirlama, anlama, uygulama, analiz, degerlendirme, yaratma

📚 Bloom seviyesi açıklamaları:
- HATIRLAMA: "Tanımlayın", "Listeleyiniz", "Ne demek?"
- ANLAMA: "Açıklayın", "Özetleyiniz", "Neden bu sonuç?"
- UYGULAMA: "Hesaplayın", "Çözün", "Uygulayın"
- ANALİZ: "Karşılaştırın", "İlişkilendiriniz", "Hangisi neden?"
- DEĞERLENDİRME: "Eleştirin", "Hangisi daha iyi?", "Doğrulayın"
- YARATMA: "Tasarlayın", "Bir model oluşturun", "Yeni bir yaklaşım önerin"
"""
    
    # ═══ YENİ: Bilgi tabanından ilgili notları çek ═══
    knowledge_base_content = ""
    try:
        from app.knowledge_base import get_relevant_knowledge
        knowledge = get_relevant_knowledge(
            topic_name=topic_data.get('konu'),
            subtopics=alt_basliklar
        )
        if knowledge:
            knowledge_base_content = f"""

═══ UZMAN BİLGİ TABANI (Bu bilgileri kullanarak DAHA DOĞRU sorular üret) ═══

{knowledge}

⚠️ ÖNEMLİ: Yukarıdaki uzman notlarındaki formülleri, kuralları ve önerileri 
soru üretiminde DOĞRU şekilde kullan. "Tipik hatalar" bölümünde belirtilen 
hataları KENDİN YAPMA.
"""
            print(f"💡 Bilgi tabanı kullanıldı: {len(knowledge)} karakter eklendi")
    except Exception as e:
        print(f"⚠️ Bilgi tabanı yüklenemedi: {e}")
    
    # ─── Buradan sonra mevcut kod devam eder ───
    
    source_section = ""
    source_json_field = ""
    if has_pages:
        source_section = f"""

═══ KAYNAK REFERANSI ═══

Bu döküman {total_pages} sayfa içerir.

📌 Üretmen gereken her soru için, dökümandan ESINLENILDIĞI yer hakkında 
detaylı bir METİN AÇIKLAMASI ver:

1. EĞER dökümanda SORU/ÖRNEK bulursan:
   - "kaynak_sayfa" = ilgili sayfa numarası (1, 2, 3, ...)
   - "kaynak_aciklama" = SPESİFİK ve DETAYLI açıklama, örnek:
     * "Sayfa 2'deki 'Soru 3'ten esinlenilmiştir. Orijinal soru: '$f(x)=x^3-6x^2+9x$ fonksiyonunun yerel ekstremum noktalarını bulunuz.' Bu sorunun katsayıları değiştirilmiştir."
     * "Sayfa 5'teki 'Örnek 2'den esinlenilmiştir. Orijinalde integral hesaplama vardı, bu soruda türev hesaplaması yapıldı."

2. EĞER sadece konu anlatımı varsa:
   - "kaynak_sayfa" = konunun en iyi açıklandığı sayfa
   - "kaynak_aciklama" = "Sayfa 3'teki 'Türev Tanımı' başlıklı konu anlatımından esinlenilmiştir. Burada limit yaklaşımıyla türev tanımlanmaktadır."

3. EĞER dökümanda ilgili içerik yoksa:
   - "kaynak_sayfa" = 0
   - "kaynak_aciklama" = "Konuya genel bilgi kullanılarak hazırlanmıştır"

⚠️ KRİTİK KURALLAR:
- "kaynak_aciklama" alanı MUTLAKA detaylı olmalı (minimum 1 cümle)
- Mümkünse ORİJİNAL sorunun/örneğin METNİNİ veya konusunu açıklamada belirt
- "Sayfa X'ten esinlenildi" gibi kısa cevaplar YETERSIZ
- kaynak_sayfa 0 olabilir ama kaynak_aciklama HER ZAMAN dolu olmalı
"""
        source_json_field = """,
      "kaynak_sayfa": 2,
      "kaynak_aciklama": "Sayfa 2'deki 'Soru 3'ten esinlenilmiştir. Orijinal: 'f(x)=x²+2x integralini hesaplayın'. Bu soruda fonksiyon değiştirilmiştir." """
    
    prompt_template = """Sen 20+ yıl deneyimli bir üniversite matematik profesörüsün. Final ve vize sınavları hazırlıyorsun.

🚫 ASLA YASAK:
- Çoktan seçmeli soru ÜRETME
- "secenekler" alanını DOLDURMA (her zaman boş liste [] olsun)
- "soru_tipi" alanına ASLA "coktan_secmeli" YAZMA
- A) B) C) D) E) şıklı sorular YASAK

✅ İZİN VERİLEN soru tipleri:
- "hesaplama", "ispat", "turetme", "analiz", "yorumlama", "uygulama"

Görev: Aşağıdaki konu için {num_questions} adet AÇIK UÇLU üniversite final sınavı sorusu üret.

═══ KONU BİLGİSİ ═══
Ana konu: {topic_data.get('konu')}
Özet: {topic_data.get('ozet')}
Alt başlıklar: {', '.join(alt_basliklar) if alt_basliklar else 'belirtilmemiş'}
Ön gereksinimler: {', '.join(on_gereksinimler) if on_gereksinimler else 'belirtilmemiş'}
Öğrencilerin tipik hataları: {', '.join(tipik_hatalar) if tipik_hatalar else 'belirtilmemiş'}
Anahtar kavramlar: {', '.join(topic_data.get('anahtar_kavramlar', []))}
═══ LATEX KULLANIM KURALLARI — ÇOK KRİTİK ═══

⚠️ MATEMATİK YAZIMI HATALARI EN BÜYÜK SORUN! Aşağıdaki kuralları MUTLAKA UYGULA:

🔴 YASAK ORTAMLAR (BU ORTAMLARI KULLANAMAZSIZ):
❌ \begin{equation}...\end{equation}
❌ \begin{gather}...\end{gather}
❌ \begin{multline}...\end{multline}
❌ \begin{array}...\end{array}

🟢 İZİN VERİLEN ORTAMLAR (BU ORTAMLARI KULLANABİLİRSİNİZ):
✅ \begin{cases}...\end{cases} — koşullu ifadeler için
✅ \begin{align}...\end{align} — çok satırlı hizalanmış denklemler için
✅ \begin{matrix}...\end{matrix} — matrisler için (parantez olmadan)
✅ \begin{pmatrix}...\end{pmatrix} — matrisler için (küçük parantez ile)
✅ \begin{bmatrix}...\end{bmatrix} — matrisler için (köşeli parantez ile)

📏 TEMEL KURALLARI:
1. HER $ VEYA $$ İFADESİ MUTLAKA TEK SATIRDA OLACAK ($...$ veya $$...$$)
   ❌ YANLIŞ: "Denklem
   $f(x) = x^2$
   şeklindedir"
   ✅ DOĞRU: "Denklem $f(x) = x^2$ şeklindedir"

2. TÜRKÇE KELİMELER MUTLAKA LaTeX DIŞINDA OLACAK
   ❌ YANLIŞ: "$f(x) = x^2 olarak tanımlanmış$"
   ✅ DOĞRU: "$f(x) = x^2$ olarak tanımlanmış"

3. ÖNEMLİ TÜRKÇE KELİMELER (bu kelimelerin $ içinde OLMAMASI GEREKİR):
   • eğer, ise, olarak, verilmiştir, için, olduğunda, noktasında, bulunuz, hesaplayınız, gösteriniz
   ✅ DOĞRU: "$x > 0$ için fonksiyon artan"
   ❌ YANLIŞ: "$x > 0 için$"

4. EĞER TÜRKÇE METNİ MUTLAKA LaTeX İÇİNDE YAZMAN GEREKIRSE, \text{} KULLANABİLİRSİN
   ✅ İYİ: "$x > 0, \text{ eğer } x \in \text{Tanım Kümesi}$"

5. BOŞ LUKLAR KRİTİK!
   ❌ YANLIŞ: "fonksiyonu $f(x) = x^2+3x$olarak" ($ sonrası boşluk yok!)
   ✅ DOĞRU: "fonksiyonu $f(x) = x^2 + 3x$ olarak" (boşluklar var)

6. LaTeX KOMUTLARI ARASI BOŞLUKLAR OLACAK
   ❌ YANLIŞ: "$\\int_C\\vec{F}\\cdotd\\vec{r}$"
   ✅ DOĞRU: "$\\int_C \\vec{F} \\cdot d\\vec{r}$"

7. NOKTA VE VİRGÜLLER LaTeX DIŞINDA OLACAK
   ❌ YANLIŞ: "$(0,0),(1,0)ve(1,1)noktaları$"
   ✅ DOĞRU: "$(0,0)$, $(1,0)$ ve $(1,1)$ noktaları"

8. KESİN KURALLARI ÖZETLERSEN:
   ✓ Her $ işareti ÖNCE ve SONRA boşluk olacak (boşluk karakteri)
   ✓ LaTeX komutları içinde TÜRKÇE KELİME OLMAYACAK (sadece \text{} içine yazılabilir)
   ✓ Türkçe bağlaç ve fiiller MUTLAKA $ DIŞINDA olacak
   ✓ Nokta, virgül, ünlem, soru işareti LaTeX DIŞINDA olacak
   ✓ Yasaklanmış ortamlar ASLA kullanılmayacak
   ✓ Boşluklar hem komutlar arasında, hem $ işaretlerinin etrafında olacak

🎯 KARŞILAŞTIRMALI ÖRNEKLER:

YANLIŞ (TEK TEK HATALAR):
1. "Fonksiyon $f(x) = x^2+3x$olarak tanımlandı" ($ sonrası boşluk yok)
2. "$\\vec{F}(x,y) = (x,y) olarak verilmiş$" (Türkçe LaTeX içinde!)
3. "$\\int_0^1 x^2 dx$hesaplayınız" (virgül eksik, boşluk yok)
4. "$(0,0)ve(1,1)noktaları$" (boşluk yok, noktalar $ içinde)

DOĞRU (AYNI SORULAR):
1. "Fonksiyon $f(x) = x^2 + 3x$ olarak tanımlandı"
2. "$\\vec{F}(x,y) = (x, y)$ olarak verilmiş"
3. "$\\int_0^1 x^2 \\, dx$ hesaplayınız"
4. "$(0, 0)$ ve $(1, 1)$ noktaları"

BÜTÜN SORU ÖRNEĞİ:

YANLIŞ:
"Vektör alanı $F(x,y)=(x^2-y,x+y^2)$ olarak verilmiştir. $C$ eğrisi, $(0,0),(1,0)ve(1,1)$ noktalarını birleştiren üçgenin sınırı olup, saat tersi yönünde yönlendirilmiştir. $\\oint_C\\vec{F}\\cdot d\\vec{r}$hesaplayınız"

DOĞRU:
"Vektör alanı $\\vec{F}(x, y) = (x^2 - y, x + y^2)$ olarak verilmiştir. $C$ eğrisi, $(0, 0)$, $(1, 0)$ ve $(1, 1)$ noktalarını birleştiren üçgenin sınırı olup, saat tersi yönünde yönlendirilmiştir.
$\\oint_C \\vec{F} \\cdot d\\vec{r}$ integrali hesaplayınız."

⚠️ EĞER BU KURALLARA UYMAZSAN SORU BOZUK GÖRÜNECEK VE KULLANICI MEMNUNİYETSİZ KALACAK.

═══ ÇÖZÜM TARZI — HOCA ANLATIYORMUŞ GİBİ ═══
⚠️ Çözüm adımları SADECE matematiksel adımlar OLMAYACAK!
Üniversitede 25+ yıl ders vermiş, sevilen bir profesör nasıl anlatıyorsa öyle yaz.

📚 HER ÇÖZÜM ADIMINDA OLMASI GEREKENLER:

1. 🎯 NEDENİ AÇIKLA — "Neden bu yöntemi seçtim?"
   ❌ KÖTÜ: "Kutupsal koordinata geçiyoruz."
   ✅ İYİ: "İntegrandda x²+y² görüyoruz — bu bize 'kutupsal!' diye bağırıyor. 
           Çünkü x²+y² = r² olur, integral muazzam basitleşir."

2. 💡 SEZGİSEL AÇIKLAMA — "Bu adım ne demek?"
   ❌ KÖTÜ: "f'(x) = 2x + 3"
   ✅ İYİ: "Türev, fonksiyonun anlık değişim hızını verir. x²'nin türevi 2x, 
           çünkü güç kuralı: x^n için türev n·x^(n-1)."

3. ⚠️ UYARI VE HATIRLATMALAR — "Burada öğrenciler hata yapar!"
   ✅ "DİKKAT: Kutupsal dönüşümde 'r' çarpanını ASLA unutma. 
       dA = r·dr·dθ olur. Bu, sınavlarda en çok yapılan hatadır."

4. 🔗 ÖNCEKİ BİLGİYLE BAĞ KUR
   ✅ "Hatırlarsan, geçen derste güç kuralını gördük. Aynı kural burada da geçerli."

5. ✓ KONTROL NOKTASI — "Doğru mu gidiyorum?"
   ✅ "Bu noktada elimde r³ ifadesi var. Mantıklı, çünkü orijinal (x²+y²)^(3/2) 
       'yi sadeleştirdik. Devam edebilirim."

📝 ÇÖZÜM ADIMI YAZIM FORMATI:

Her adım MİNİMUM 2-3 cümle olmalı:
- 1. cümle: NE yapıyoruz?
- 2. cümle: NEDEN bunu yapıyoruz veya NASIL çalışıyor?
- 3. cümle (opsiyonel): UYARI, İPUCU veya BAĞLANTI

🚫 KESİNLİKLE YAPMA:
- "Adım 1: İntegrali hesapla" (çok kısa)
- "Sonuç: 31π/10" (açıklamasız)
- Tek satırlık matematiksel ifadeler
- "Bunu yapıp diğerine geç" gibi belirsiz cümleler

✅ HEDEF: Öğrenci çözümü okudukça sadece NE değil, NEDEN ve NASIL'ı da öğrenmeli.

📖 ÖRNEK İYİ ÇÖZÜM ADIMI:

"Adım 2 — Kutupsal Koordinatlara Geçiş:

Şimdi sıkı durun, sihirli kısma geliyoruz! Kutupsal koordinatta x = r·cos(θ) 
ve y = r·sin(θ) tanımları var. Bunu integrandımıza yerleştirdiğimizde:

  x² + y² = r²·cos²(θ) + r²·sin²(θ) = r²·(cos²θ + sin²θ) = r²

Çünkü temel trigonometrik özdeşliği biliyorsun: cos²θ + sin²θ = 1.

Yani (x²+y²)^(3/2) = (r²)^(3/2) = r³ olur. Çok daha sade, değil mi?

⚠️ ÖNEMLİ UYARI: Burada en sık yapılan hata, dA = dx·dy yazmak. 
HAYIR! Kutupsal koordinatta alan elemanı dA = r·dr·dθ olur. 
Bu 'r' çarpanı Jacobi determinantından gelir ve UNUTULMAMALIDIR."
{knowledge_base_content}
{bloom_section}
{source_section}

═══ GRAFİK (SVG) DESTEĞİ ═══

Bazı sorular grafik gerektirir (fonksiyon grafiği, geometri, vektör vb.). Gerekirse SVG ekle:

🎨 SVG Kuralları:
- viewBox="0 0 400 300"
- Çizgi rengi: #2d3748
- Etiketler için <text>
- Eksenler için ok ucu

Örnek SVG şablonu:
<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
  <line x1="50" y1="150" x2="370" y2="150" stroke="#2d3748" stroke-width="2"/>
  <line x1="200" y1="280" x2="200" y2="20" stroke="#2d3748" stroke-width="2"/>
  <text x="375" y="155" font-size="14">x</text>
  <text x="205" y="20" font-size="14">y</text>
  <path d="M 100,250 Q 200,-50 300,250" stroke="#6366f1" stroke-width="2" fill="none"/>
  ═══════════════════════════════════════════════════════════
🎨 GRAFİK ÜRETİMİ — MUTLAK KURALLAR (DİKKATLE OKU!)
═══════════════════════════════════════════════════════════

⚠️ KRİTİK KURAL: 
"has_graph": true diyorsan, "graph_data" alanını DOLDURMAK ZORUNDASIN!
BOŞ {} GÖNDEREMEZSİN. NULL GÖNDEREMEZSİN.

İKİ SEÇENEĞİN VAR:
 ✅ SEÇENEK A: "has_graph": false → "graph_data": null (grafik yok)
 ✅ SEÇENEK B: "has_graph": true → "graph_data": {DOLU OBJE} (grafik var)
 ❌ YANLIŞ: "has_graph": true → "graph_data": {} (BOŞ obje YASAK!)

🔥 ALTIN KURAL:
Eğer grafiği nasıl yapısallaştıracağını bilmiyorsan, 
"has_graph": false yap. ASLA boş graph_data gönderme.

═══════════════════════════════════════════════════════════
📊 GRAFİK FORMATLARI (Birini SEÇMEK ZORUNDASIN)
═══════════════════════════════════════════════════════════

▸ TİP 1: FONKSİYON GRAFİĞİ — En yaygın, çoğu durumda bunu kullan
{
    "graph_type": "function",
    "functions": [
        {"expr": "x**2", "label": "f(x) = x²"},
        {"expr": "2*x + 1", "label": "g(x) = 2x+1"}
    ],
    "x_range": [-5, 5],
    "title": "Fonksiyon Grafikleri"
}

▸ TİP 2: BELİRLİ İNTEGRAL ALANI
{
    "graph_type": "integral",
    "function": "x**2",
    "integral_range": [0, 2],
    "x_range": [-1, 3],
    "title": "Belirli İntegral",
    "show_value": "Alan = 8/3"
}

▸ TİP 3: TÜREV / TEĞET DOĞRUSU
{
    "graph_type": "derivative",
    "function": "x**2",
    "derivative": "2*x",
    "point": 1,
    "x_range": [-3, 3],
    "title": "x=1 Noktasında Teğet"
}

▸ TİP 4: KRİTİK NOKTALAR (Max/Min)
{
    "graph_type": "critical_points",
    "function": "x**3 - 3*x",
    "x_range": [-3, 3],
    "points": [
        {"x": 1, "y": -2, "label": "Min"},
        {"x": -1, "y": 2, "label": "Max"}
    ]
}

═══════════════════════════════════════════════════════════
🔧 FONKSİYON YAZIM KURALLARI (HATA YAPMA!)
═══════════════════════════════════════════════════════════

✅ DOĞRU Python syntax:
   • x**2  (kare için)
   • 2*x   (çarpma için)
   • sin(x), cos(x), tan(x)
   • sqrt(x), exp(x), log(x)
   • pi, e (sabitler)

❌ YANLIŞ (yazma!):
   • x^2  (caret YASAK)
   • 2x   (çarpma yıldızı eksik YASAK)
   • Sin(x)  (büyük harf YASAK)

═══════════════════════════════════════════════════════════
🎯 GRAFİK ZORUNLU OLAN SORU TİPLERİ
═══════════════════════════════════════════════════════════

Şu durumlarda has_graph=true olmalı VE graph_data dolu olmalı:

✓ "Grafiğini çizin" diyorsa → TİP 1 (function)
✓ "Alanını bulun", "İntegralin değeri" → TİP 2 (integral)
✓ "Teğet doğru", "x=X noktasında türev" → TİP 3 (derivative)
✓ "Max/min noktaları", "Yerel ekstremum" → TİP 4 (critical_points)
✓ "Kesişim noktaları" → TİP 1 (function, çoklu)

═══════════════════════════════════════════════════════════
📝 ÖRNEK: BELİRLİ İNTEGRAL SORUSU
═══════════════════════════════════════════════════════════

SORU: "f(x) = x² fonksiyonunun [0, 2] aralığındaki belirli integralini hesaplayın."

✅ DOĞRU CEVAP YAPISI:
{
    "soru_metni": "f(x) = x² fonksiyonunun [0, 2]...",
    "has_graph": true,
    "graph_description": "x² parabolünün [0,2] aralığındaki x ekseni ile arasındaki alan",
    "graph_data": {
        "graph_type": "integral",
        "function": "x**2",
        "integral_range": [0, 2],
        "x_range": [-0.5, 2.5],
        "title": "f(x) = x² için [0,2] Alanı",
        "show_value": "Alan = 8/3 ≈ 2.67"
    },
    ...diğer alanlar...
}

❌ YANLIŞ CEVAP (YAPMA!):
{
    "has_graph": true,
    "graph_data": {}  ← BOŞ! HATA!
}

❌ YANLIŞ CEVAP (YAPMA!):
{
    "has_graph": true,
    "graph_data": null  ← NULL! HATA!
}

═══════════════════════════════════════════════════════════
⚠️ SON UYARI
═══════════════════════════════════════════════════════════

Eğer "has_graph: true" diyorsan ama yukarıdaki 4 tipten birini 
KULLANAMIYORSAN, o zaman "has_graph: false" yap. 

Yarım grafikten, hiç grafik daha iyidir.

🔧 FONKSİYON YAZIM KURALLARI:
✓ Python syntax kullan: x**2 (x² için), 2*x (2x için), sqrt(x) gibi
✓ ASLA: x^2 (yanlış!), 2x (yanlış!)
✓ Trigonometri: sin(x), cos(x), tan(x)
✓ Logaritma: log(x) (doğal log), log10(x), exp(x)
✓ Sabit: pi, e (her ikisi de kullanılabilir)

📐 KARARLI X-ARALIK SEÇİMİ:
✓ Polinom: [-5, 5] genelde iyi
✓ Trigonometrik: [-2*pi, 2*pi] veya [-pi, pi]
✓ Üstel: [-3, 3]
✓ Logaritma: [0.1, 10] (negatif olmasın!)

⚠️ NE ZAMAN has_graph = true YAPMALI:
✓ Soru "grafiğini çizin", "şeklini gösterin" diyorsa
✓ Soru "kesişim noktası", "alan", "teğet" gibi görsel kavramları içeriyorsa
✓ Maksimum/minimum bulma, türev görselleştirme
✗ İspat sorularında genelde gerek yok
✗ Sadece hesaplama isteyen sorularda genelde gerek yok

📝 ÖRNEK SORU + GRAFİK:

SORU: "f(x) = x² fonksiyonunun [0, 2] aralığındaki alanını hesaplayın."

CEVAP:
{
    "soru_metni": "...",
    "has_graph": true,
    "graph_description": "f(x) = x² fonksiyonu ile x ekseni arasında [0,2] aralığında kalan alan gösterilmiştir.",
    "graph_data": {
        "graph_type": "integral",
        "function": "x**2",
        "integral_range": [0, 2],
        "x_range": [-0.5, 2.5],
        "title": "f(x) = x² için [0,2] Alanı",
        "show_value": "Alan = 8/3"
    },
</svg>

Grafik gereksiz ise has_graph=false, graph_svg="" yap.

═══ MATEMATİK FORMATLAMA ═══

⚠️ TÜM matematik ifadelerini $...$ ile sar:
- "Doğru cevap: $\\\\frac{{\\\\pi}}{{4}}$"
- "Sonuç: $\\\\int_0^1 x dx = \\\\frac{{1}}{{2}}$"

═══ ZORLUK DAĞILIMI ═══
1. soru: KOLAY | 2. soru: ORTA | 3. soru: ZOR

═══ ÇIKTI FORMATI (SADECE JSON) ═══

{{
  "sorular": [
    {{
      "soru_metni": "Sorunun tam akademik metni",
      "soru_tipi": "hesaplama VEYA ispat VEYA turetme VEYA analiz VEYA yorumlama VEYA uygulama",
      "zorluk": "kolay veya orta veya zor",
      "olculen_kavram": "Hangi kavramı ölçtüğü",
      "secenekler": [],
      "cozum_adimlari": [
        "Adım 1: ...",
        "Adım 2: ...",
        "Adım 3: ..."
      ],
      "dogru_cevap": "$...$ İÇİNDE matematik ifade",
      "ipucu": "Tek cümlelik ipucu",
      "bloom_seviyesi": "uygulama",
      "has_graph": false,
      "graph_svg": "",
      "graph_data": null
      {{
  "sorular": [
    {{
      ...
      "has_graph": true,
      "graph_description": "f(x)=x² parabolün grafiği",
      "graph_data": {{
        "graph_type": "function",
        "functions": [{{"expr": "x**2", "label": "f(x) = x²"}}],
        "x_range": [-3, 3],
        "title": "Parabol Grafiği"
      }}      
    }}
  ]
}}

═══ JSON KAÇIŞ KARAKTER KURALLARI ═══

JSON'daki TÜM backslash'leri ÇİFT YAP:
- $\\\\sqrt{{x}}$, $\\\\frac{{a}}{{b}}$, $\\\\int$, $\\\\infty$, $\\\\pi$

═══ KRİTİK KURALLAR ÖZETİ ═══
1. SADECE JSON dön
2. "secenekler" her zaman []
3. "soru_tipi" ASLA "coktan_secmeli" olmaz
4. "dogru_cevap" MUTLAKA $...$ içinde matematik"""
    prompt = (
        prompt_template
        .replace('{num_questions}', str(num_questions))
        .replace("{topic_data.get('konu')}", str(topic_data.get('konu', '')))
        .replace("{topic_data.get('ozet')}", str(topic_data.get('ozet', '')))
        .replace("{', '.join(alt_basliklar) if alt_basliklar else 'belirtilmemiş'}", ', '.join(alt_basliklar) if alt_basliklar else 'belirtilmemiş')
        .replace("{', '.join(on_gereksinimler) if on_gereksinimler else 'belirtilmemiş'}", ', '.join(on_gereksinimler) if on_gereksinimler else 'belirtilmemiş')
        .replace("{', '.join(tipik_hatalar) if tipik_hatalar else 'belirtilmemiş'}", ', '.join(tipik_hatalar) if tipik_hatalar else 'belirtilmemiş')
        .replace("{', '.join(topic_data.get('anahtar_kavramlar', []))}", ', '.join(topic_data.get('anahtar_kavramlar', [])))
        .replace('{knowledge_base_content}', knowledge_base_content)
        .replace('{bloom_section}', bloom_section)
        .replace('{source_section}', source_section)
    )
    config = {'response_mime_type': 'application/json', 'response_schema': get_questions_schema(has_pages)}
    response = call_with_retry(
        lambda: client.models.generate_content(
            model=GENERATION_MODEL,
            contents=prompt,
            config=config
        ),
        max_retries=5,
        context="generate_questions"
    )
    
    return response.text


# ═══════════════════════════════════════════
# TELEMETRİ — debug için
# ═══════════════════════════════════════════

def get_stats():
    """Sistem istatistiklerini döner. Debug için."""
    return {
        'success': dict(success_stats),
        'errors': dict(error_stats),
    }


def print_stats():
    """İstatistikleri ekrana yazdırır."""
    print("\n📊 EduScan AI Service İstatistikleri:")
    print(f"  ✅ Başarılı çağrılar:")
    for ctx, count in success_stats.items():
        print(f"    - {ctx}: {count}")
    print(f"  ❌ Hatalar:")
    for category, count in error_stats.items():
        print(f"    - {category}: {count}")
