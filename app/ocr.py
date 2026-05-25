import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from dotenv import load_dotenv

load_dotenv()

TESSERACT_PATH = os.getenv('TESSERACT_PATH')
POPPLER_PATH = os.getenv('POPPLER_PATH')

if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def extract_text_from_image(image_path):
    """Bir görüntü dosyasından (JPG, PNG) metin çıkarır."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='tur+eng', config='--psm 6 --oem 3')
        return text.strip()
    except Exception as e:
        return f"HATA: Görüntü işlenemedi - {str(e)}"


def extract_text_from_pdf(pdf_path):
    """Bir PDF dosyasını sayfa sayfa görüntüye çevirip OCR uygular."""
    try:
        pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=200)
        
        all_text = []
        for i, page in enumerate(pages, start=1):
            page_text = pytesseract.image_to_string(page, lang='tur+eng', config='--psm 6 --oem 3')
            all_text.append(f"--- Sayfa {i} ---\n{page_text.strip()}")
        
        return "\n\n".join(all_text)
    except Exception as e:
        return f"HATA: PDF işlenemedi - {str(e)}"


def extract_text(file_path):
    """Dosya tipine göre uygun OCR fonksiyonunu çağırır."""
    if not os.path.exists(file_path):
        return "HATA: Dosya bulunamadı"
    
    extension = file_path.lower().split('.')[-1]
    
    if extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
        return extract_text_from_image(file_path)
    else:
        return f"HATA: Desteklenmeyen dosya tipi: {extension}"