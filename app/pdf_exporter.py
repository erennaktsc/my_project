import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def clean_latex_for_pdf(text):
    """LaTeX ifadelerini PDF'te okunabilir hale getirir."""
    if not text:
        return ''
    
    # $...$ işaretlerini kaldır
    text = re.sub(r'\$+', '', text)
    
    # Yaygın LaTeX komutları → unicode/text karşılıkları
    replacements = {
        r'\\frac\{([^}]+)\}\{([^}]+)\}': r'(\1)/(\2)',
        r'\\sqrt\{([^}]+)\}': r'√(\1)',
        r'\\sqrt': '√',
        r'\\pi': 'π',
        r'\\infty': '∞',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\theta': 'θ',
        r'\\lambda': 'λ',
        r'\\mu': 'μ',
        r'\\sigma': 'σ',
        r'\\sum': '∑',
        r'\\prod': '∏',
        r'\\int': '∫',
        r'\\lim': 'lim',
        r'\\to': '→',
        r'\\leftarrow': '←',
        r'\\Rightarrow': '⇒',
        r'\\Leftrightarrow': '⇔',
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\neq': '≠',
        r'\\approx': '≈',
        r'\\pm': '±',
        r'\\times': '×',
        r'\\div': '÷',
        r'\\cdot': '·',
        r'\\in': '∈',
        r'\\notin': '∉',
        r'\\subset': '⊂',
        r'\\cup': '∪',
        r'\\cap': '∩',
        r'\\forall': '∀',
        r'\\exists': '∃',
        r'\\partial': '∂',
        r'\\nabla': '∇',
        r'\\mathbb\{R\}': 'ℝ',
        r'\\mathbb\{N\}': 'ℕ',
        r'\\mathbb\{Z\}': 'ℤ',
        r'\\mathbb\{Q\}': 'ℚ',
        r'\\mathbb\{C\}': 'ℂ',
        r'\\mathbb\{([^}]+)\}': r'\1',
        r'\\left': '',
        r'\\right': '',
        r'\\\\': '\n',
        r'\\,': ' ',
        r'\\;': ' ',
        r'\\ ': ' ',
        r'\^\{([^}]+)\}': r'^(\1)',
        r'_\{([^}]+)\}': r'_(\1)',
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    
    # Kalan backslash'leri temizle
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)
    
    # HTML entities
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('&amp;lt;', '&lt;').replace('&amp;gt;', '&gt;')
    
    return text


def generate_questions_pdf(document, topics_with_questions, output_path):
    """
    Bir dokümandaki soruları PDF olarak üretir.
    
    Args:
        document: Document modeli
        topics_with_questions: [{'topic': Topic, 'questions': [Question, ...]}, ...]
        output_path: Çıktı dosyası yolu
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Özel stiller
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=HexColor('#6366f1'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#6b7280'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    topic_style = ParagraphStyle(
        'TopicStyle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=HexColor('#4f46e5'),
        spaceAfter=10,
        spaceBefore=15
    )
    
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#4b5563'),
        spaceAfter=15,
        leftIndent=10,
        rightIndent=10,
        backColor=HexColor('#f3f4f6'),
        borderPadding=10,
        leading=14
    )
    
    question_num_style = ParagraphStyle(
        'QuestionNum',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=HexColor('#111827'),
        spaceAfter=5
    )
    
    question_meta_style = ParagraphStyle(
        'QuestionMeta',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#6b7280'),
        spaceAfter=8
    )
    
    question_text_style = ParagraphStyle(
        'QuestionText',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#111827'),
        spaceAfter=10,
        leading=16
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#374151'),
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    solution_style = ParagraphStyle(
        'SolutionStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#1f2937'),
        spaceAfter=4,
        leftIndent=15,
        leading=14
    )
    
    answer_style = ParagraphStyle(
        'AnswerStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#065f46'),
        spaceAfter=10,
        leftIndent=10,
        backColor=HexColor('#d1fae5'),
        borderPadding=8,
        fontName='Helvetica-Bold'
    )
    
    # PDF içeriği
    story = []
    
    # Başlık
    story.append(Paragraph('📚 EduScan — Sınav Soruları', title_style))
    story.append(Paragraph(
        f'<b>Doküman:</b> {document.filename}<br/><b>Tarih:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}',
        subtitle_style
    ))
    story.append(Spacer(1, 0.5*cm))
    
    # Her konu ve soruları
    for item in topics_with_questions:
        topic = item['topic']
        questions = item['questions']
        
        # Konu başlığı
        story.append(Paragraph(f'📖 {topic.topic_name}', topic_style))
        
        # Özet
        if topic.summary:
            story.append(Paragraph(f'<b>Özet:</b> {topic.summary}', summary_style))
        
        story.append(Spacer(1, 0.3*cm))
        
        # Sorular
        for idx, q in enumerate(questions, start=1):
            # Soru numarası
            story.append(Paragraph(f'Soru {idx}', question_num_style))
            
            # Meta bilgiler
            meta = f'<b>Zorluk:</b> {q.difficulty.upper()} | <b>Tip:</b> {q.question_type.replace("_", " ")}'
            if q.measured_concept:
                meta += f' | <b>Ölçülen:</b> {q.measured_concept}'
            story.append(Paragraph(meta, question_meta_style))
            
            # Soru metni
            soru_metni = clean_latex_for_pdf(q.question_text)
            story.append(Paragraph(soru_metni, question_text_style))
            
            # İpucu
            if q.hint:
                story.append(Paragraph('💡 <b>İpucu:</b>', label_style))
                ipucu = clean_latex_for_pdf(q.hint)
                story.append(Paragraph(ipucu, solution_style))
                story.append(Spacer(1, 0.2*cm))
            
            # Çözüm
            if q.solution_steps:
                story.append(Paragraph('📋 <b>Çözüm Adımları:</b>', label_style))
                steps = q.solution_steps.split('\n')
                for step in steps:
                    if step.strip():
                        step_clean = clean_latex_for_pdf(step.strip())
                        story.append(Paragraph(f'• {step_clean}', solution_style))
                story.append(Spacer(1, 0.2*cm))
            
            # Doğru cevap
            if q.correct_answer:
                cevap = clean_latex_for_pdf(q.correct_answer)
                story.append(Paragraph(f'✓ <b>Doğru Cevap:</b> {cevap}', answer_style))
            
            story.append(Spacer(1, 0.5*cm))
        
        # Konular arası sayfa atla
        if item != topics_with_questions[-1]:
            story.append(PageBreak())
    
    # Footer (en sayfada)
    story.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#9ca3af'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(
        '📚 EduScan — Yapay Zeka Destekli Sınav Hazırlık Sistemi<br/>'
        f'Bu doküman {datetime.now().strftime("%d.%m.%Y")} tarihinde otomatik olarak oluşturulmuştur.',
        footer_style
    ))
    
    # PDF oluştur
    doc.build(story)
    return output_path