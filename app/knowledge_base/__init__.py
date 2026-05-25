"""
EduScan Bilgi Tabanı (Knowledge Base) Sistemi
=============================================

Bu modül, AI'nın iyi olmadığı alanlarda bilgi enjeksiyonu yaparak
soru üretim kalitesini artırır.

Kullanım:
    from app.knowledge_base import get_relevant_knowledge
    
    knowledge = get_relevant_knowledge("Çok Katlı İntegraller")
    # knowledge artık AI'ya verilebilecek detaylı bilgi içerir
"""

from app.knowledge_base.topic_matcher import (
    get_relevant_knowledge,
    detect_category,
    list_available_categories
)

__all__ = [
    'get_relevant_knowledge',
    'detect_category', 
    'list_available_categories'
]