import os
from datetime import datetime
from pdf2image import convert_from_path
from PIL import Image
from dotenv import load_dotenv
import shutil
load_dotenv()

POPPLER_PATH = os.getenv('POPPLER_PATH')


def pdf_to_page_images(pdf_path, output_folder='uploads/sources'):
    """
    PDF'i sayfa sayfa görüntüye çevirir.
    Her sayfayı output_folder içine kaydeder.
    Geri dönüş: [(sayfa_no, dosya_yolu), ...]
    """
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=150)
    
    page_paths = []
    for i, page in enumerate(pages, start=1):
        page_filename = f"{timestamp}_page{i}.png"
        page_path = os.path.join(output_folder, page_filename)
        page.save(page_path, 'PNG')
        page_paths.append((i, page_path))
    
    return page_paths


def crop_question_region(page_image_path, bbox, output_folder='uploads/sources/cropped'):
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        image = Image.open(page_image_path)
        img_w, img_h = image.size
        
        x = bbox.get('x', 0)
        y = bbox.get('y', 0)
        w = bbox.get('width', img_w)
        h = bbox.get('height', img_h)
        
        # ⚠️ Geçersiz/anlamsız bbox kontrolü
        # Eğer AI hiç bbox vermemişse veya çok küçükse, sayfanın TAMAMINI ver
        if w < 50 or h < 50 or (x == 0 and y == 0 and w == 0 and h == 0):
            # Tüm sayfayı kaynak olarak kullan
            print(f"⚠️ Anlamsız bbox geldi, tüm sayfa kaydedilecek")
            cropped = image.copy()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            crop_filename = f"crop_{timestamp}.png"
            crop_path = os.path.join(output_folder, crop_filename)
            cropped.save(crop_path, 'PNG')
            return crop_path
        
        # Normal koordinat dönüşümü
        if max(x, y, x+w, y+h) <= 1000:
            x = int(x / 1000 * img_w)
            y = int(y / 1000 * img_h)
            w = int(w / 1000 * img_w)
            h = int(h / 1000 * img_h)
        
        # Güvenlik
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        
        # Padding
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img_w - x, w + 2 * padding)
        h = min(img_h - y, h + 2 * padding)
        
        cropped = image.crop((x, y, x + w, y + h))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        crop_filename = f"crop_{timestamp}.png"
        crop_path = os.path.join(output_folder, crop_filename)
        cropped.save(crop_path, 'PNG')
        
        return crop_path
    
    except Exception as e:
        print(f"⚠️ Kırpma hatası: {e}")
        return None

def save_full_page_as_source(page_image_path):
    """
    Sayfa görüntüsünü kaynak klasörüne kopyalar (kırpma YAPMAZ).
    
    Args:
        page_image_path: Sayfanın orijinal görüntü yolu
    
    Returns:
        Yeni kopya dosyanın yolu, veya None hata olursa
    """
    if not page_image_path or not os.path.exists(page_image_path):
        return None
    
    try:
        # Kaynak klasörü oluştur
        output_dir = 'uploads/sources/pages'
        os.makedirs(output_dir, exist_ok=True)
        
        # Benzersiz dosya adı oluştur
        original_name = os.path.basename(page_image_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        new_name = f"page_{timestamp}_{original_name}"
        new_path = os.path.join(output_dir, new_name)
        
        # Kopyala
        shutil.copy2(page_image_path, new_path)
        
        return new_path
    
    except Exception as e:
        print(f"⚠️ Sayfa kaydetme hatası: {e}")
        return None

def image_to_page_image(image_path, output_folder='uploads/sources'):
    """
    Görüntü dosyası ise tek sayfa olarak kabul et, kopyala.
    """
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_page1.png"
    target_path = os.path.join(output_folder, filename)
    
    # PIL ile aç ve PNG olarak kaydet (format dönüşümü için)
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(target_path, 'PNG')
    
    return [(1, target_path)]