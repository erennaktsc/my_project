"""
EduScan Grafik Üreteci
=======================

AI'dan gelen yapısal veri ile Matplotlib kullanarak SVG grafik üretir.
"""
import matplotlib
matplotlib.use('Agg')  # GUI backend kapalı (server için kritik)

import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import re
from collections import defaultdict


# Telemetri
graph_stats = defaultdict(int)


# ═══════════════════════════════════════════
# STIL AYARLARI
# ═══════════════════════════════════════════

def setup_style():
    """Modern matematik kitabı stilini ayarlar."""
    plt.rcParams.update({
        'font.size': 11,
        'font.family': 'sans-serif',
        'axes.titlesize': 13,
        'axes.titleweight': 'bold',
        'axes.labelsize': 11,
        'axes.linewidth': 1.2,
        'axes.edgecolor': '#4b5563',
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
        'grid.linewidth': 0.6,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'legend.framealpha': 0.95,
        'legend.edgecolor': '#9ca3af',
        'figure.facecolor': 'white',
        'axes.facecolor': '#fafbff'
    })


# ═══════════════════════════════════════════
# FONKSIYON PARSE — GÜVENLI EVAL
# ═══════════════════════════════════════════

def safe_function_eval(expr_str, x):
    """
    Güvenli bir şekilde matematik ifadesini değerlendir.
    
    Args:
        expr_str: Fonksiyon ifadesi (ör: 'x**2 + 3*x')
        x: numpy array
    
    Returns:
        numpy array veya None
    """
    if not expr_str:
        return None
    
    # Güvenli isimler — sadece matematik
    safe_names = {
        'x': x,
        'np': np,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
        'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
        'exp': np.exp, 'log': np.log, 'log2': np.log2, 'log10': np.log10,
        'sqrt': np.sqrt, 'abs': np.abs,
        'pi': np.pi, 'e': np.e,
        'ceil': np.ceil, 'floor': np.floor,
        'power': np.power, 'pow': np.power
    }
    
    # AI bazen ^ kullanır, ** yap
    expr_str = expr_str.replace('^', '**')
    
    # Türkçe karakter düzeltmeleri
    expr_str = expr_str.replace('π', 'pi')
    
    try:
        # eval ile değerlendir (sadece safe_names erişimi)
        result = eval(expr_str, {"__builtins__": {}}, safe_names)
        
        # NaN ve Inf değerleri filtrele
        if hasattr(result, '__iter__'):
            result = np.array(result, dtype=float)
            result[np.isinf(result)] = np.nan
        
        return result
    except Exception as e:
        print(f"⚠️ Fonksiyon parse hatası: {expr_str} → {e}")
        return None


# ═══════════════════════════════════════════
# GRAFİK ÜRETİCİLER
# ═══════════════════════════════════════════

def create_function_plot(graph_data):
    """
    Fonksiyon grafiği üretir.
    
    Beklenen veri yapısı:
    {
        "graph_type": "function",
        "functions": [
            {"expr": "x**2", "label": "f(x) = x²", "color": "blue"},
            {"expr": "2*x + 1", "label": "g(x) = 2x+1", "color": "red"}
        ],
        "x_range": [-5, 5],
        "title": "Fonksiyon Grafikleri",
        "annotations": [
            {"x": 1, "y": 1, "text": "(1,1) Kesişim"}
        ]
    }
    """
    setup_style()
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    
    # X aralığı
    x_range = graph_data.get('x_range', [-5, 5])
    x = np.linspace(x_range[0], x_range[1], 500)
    
    # Fonksiyonları çiz
    functions = graph_data.get('functions', [])
    default_colors = ['#6366f1', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
    
    plotted = False
    for i, func in enumerate(functions):
        if isinstance(func, str):
            # Eski format: sadece string
            expr = func
            label = f'f_{i+1}(x)'
            color = default_colors[i % len(default_colors)]
        else:
            expr = func.get('expr', '')
            label = func.get('label', f'f_{i+1}(x)')
            color = func.get('color') or default_colors[i % len(default_colors)]
        
        y = safe_function_eval(expr, x)
        if y is not None and not np.all(np.isnan(y)):
            ax.plot(x, y, label=label, color=color, linewidth=2.2)
            plotted = True
    
    if not plotted:
        plt.close(fig)
        return None
    
    # Eksenler
    ax.axhline(y=0, color='#374151', linewidth=0.8, alpha=0.7)
    ax.axvline(x=0, color='#374151', linewidth=0.8, alpha=0.7)
    
    # Başlık
    title = graph_data.get('title', '')
    if title:
        ax.set_title(title, pad=15)
    
    # Eksen etiketleri
    ax.set_xlabel('x', fontsize=12, style='italic')
    ax.set_ylabel('y', fontsize=12, style='italic')
    
    # Annotations (özel noktalar)
    annotations = graph_data.get('annotations', [])
    for ann in annotations:
        ax_x = ann.get('x')
        ax_y = ann.get('y')
        text = ann.get('text', '')
        
        if ax_x is not None and ax_y is not None:
            ax.plot(ax_x, ax_y, 'o', color='#dc2626', markersize=9, 
                    markeredgecolor='white', markeredgewidth=1.5, zorder=5)
            if text:
                ax.annotate(text, xy=(ax_x, ax_y), xytext=(8, 8),
                            textcoords='offset points', fontsize=10,
                            bbox=dict(boxstyle='round,pad=0.4',
                                      facecolor='#fef3c7',
                                      edgecolor='#f59e0b',
                                      alpha=0.95))
    
    # Legend
    if len(functions) > 0:
        ax.legend(loc='best', fontsize=10, framealpha=0.95)
    
    # Y aralığı otomatik (NaN'larsız)
    ax.autoscale(enable=True, axis='y', tight=False)
    
    # Margin
    ax.margins(x=0.02, y=0.1)
    
    return save_to_svg(fig)


def create_integral_plot(graph_data):
    """
    İntegral alanını gölgelendirilmiş grafiği üretir.
    
    Beklenen veri yapısı:
    {
        "graph_type": "integral",
        "function": "x**2",
        "integral_range": [0, 2],
        "x_range": [-1, 3],
        "title": "Belirli İntegral",
        "show_value": "∫₀² x² dx = 8/3"
    }
    """
    setup_style()
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    
    # X aralığı
    x_range = graph_data.get('x_range', [-5, 5])
    x = np.linspace(x_range[0], x_range[1], 500)
    
    # Fonksiyon
    expr = graph_data.get('function', '')
    y = safe_function_eval(expr, x)
    
    if y is None:
        plt.close(fig)
        return None
    
    # Ana eğri
    ax.plot(x, y, color='#6366f1', linewidth=2.5, 
            label=f'f(x) = {expr.replace("**", "^")}')
    
    # İntegral aralığı
    int_range = graph_data.get('integral_range', [0, 1])
    a, b = int_range[0], int_range[1]
    
    # Gölgelendirilmiş alan
    x_fill = np.linspace(a, b, 200)
    y_fill = safe_function_eval(expr, x_fill)
    
    if y_fill is not None:
        ax.fill_between(x_fill, 0, y_fill, alpha=0.4, color='#fbbf24',
                        label=f'Alan: [{a}, {b}]')
        
        # Sınır çizgileri
        ax.axvline(x=a, color='#dc2626', linestyle='--', linewidth=1.5, alpha=0.7)
        ax.axvline(x=b, color='#dc2626', linestyle='--', linewidth=1.5, alpha=0.7)
        
        # Etiketler
        ax.text(a, ax.get_ylim()[0]*0.95, f'a={a}', 
                ha='center', fontsize=10, color='#dc2626', fontweight='bold')
        ax.text(b, ax.get_ylim()[0]*0.95, f'b={b}', 
                ha='center', fontsize=10, color='#dc2626', fontweight='bold')
    
    # Eksenler
    ax.axhline(y=0, color='#374151', linewidth=0.8, alpha=0.7)
    ax.axvline(x=0, color='#374151', linewidth=0.8, alpha=0.7)
    
    # Başlık
    title = graph_data.get('title', f'∫ f(x) dx — [{a}, {b}]')
    ax.set_title(title, pad=15)
    
    # İntegral değeri (varsa)
    show_value = graph_data.get('show_value', '')
    if show_value:
        ax.text(0.02, 0.98, show_value, transform=ax.transAxes,
                fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.5',
                          facecolor='#dbeafe',
                          edgecolor='#6366f1', alpha=0.95))
    
    ax.set_xlabel('x', fontsize=12, style='italic')
    ax.set_ylabel('y', fontsize=12, style='italic')
    ax.legend(loc='best', fontsize=10)
    ax.margins(x=0.02, y=0.1)
    
    return save_to_svg(fig)


def create_derivative_plot(graph_data):
    """
    Fonksiyon ve teğet doğrusunu çizer.
    
    Beklenen veri yapısı:
    {
        "graph_type": "derivative",
        "function": "x**2",
        "derivative": "2*x",
        "point": 1,
        "x_range": [-3, 3],
        "title": "Türev ve Teğet"
    }
    """
    setup_style()
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    
    # X aralığı
    x_range = graph_data.get('x_range', [-3, 3])
    x = np.linspace(x_range[0], x_range[1], 500)
    
    # Ana fonksiyon
    expr = graph_data.get('function', '')
    y = safe_function_eval(expr, x)
    
    if y is None:
        plt.close(fig)
        return None
    
    ax.plot(x, y, color='#6366f1', linewidth=2.5, 
            label=f'f(x) = {expr.replace("**", "^")}')
    
    # Teğet noktası
    point_x = graph_data.get('point', 0)
    point_y = safe_function_eval(expr, np.array([point_x]))
    
    if point_y is not None and not np.isnan(point_y[0]):
        point_y_val = point_y[0]
        
        # Türev değeri
        deriv_expr = graph_data.get('derivative', '')
        if deriv_expr:
            slope = safe_function_eval(deriv_expr, np.array([point_x]))
            if slope is not None and not np.isnan(slope[0]):
                slope_val = slope[0]
                
                # Teğet doğrusu: y = slope*(x - point_x) + point_y_val
                tangent_y = slope_val * (x - point_x) + point_y_val
                ax.plot(x, tangent_y, color='#dc2626', linewidth=2, 
                        linestyle='--', 
                        label=f'Teğet: y = {slope_val:.2f}(x - {point_x}) + {point_y_val:.2f}')
        
        # Nokta işareti
        ax.plot(point_x, point_y_val, 'o', color='#dc2626', markersize=10,
                markeredgecolor='white', markeredgewidth=2, zorder=5)
        ax.annotate(f'({point_x}, {point_y_val:.2f})',
                    xy=(point_x, point_y_val), xytext=(10, 10),
                    textcoords='offset points', fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.4',
                              facecolor='#fef3c7', edgecolor='#f59e0b'))
    
    # Eksenler
    ax.axhline(y=0, color='#374151', linewidth=0.8, alpha=0.7)
    ax.axvline(x=0, color='#374151', linewidth=0.8, alpha=0.7)
    
    title = graph_data.get('title', 'Türev ve Teğet Doğrusu')
    ax.set_title(title, pad=15)
    
    ax.set_xlabel('x', fontsize=12, style='italic')
    ax.set_ylabel('y', fontsize=12, style='italic')
    ax.legend(loc='best', fontsize=10)
    ax.margins(x=0.02, y=0.1)
    
    return save_to_svg(fig)


def create_points_plot(graph_data):
    """
    Fonksiyon + kritik noktalar grafiği.
    
    Beklenen veri yapısı:
    {
        "graph_type": "critical_points",
        "function": "x**3 - 3*x",
        "x_range": [-3, 3],
        "points": [
            {"x": 1, "y": -2, "label": "Min", "color": "green"},
            {"x": -1, "y": 2, "label": "Max", "color": "red"}
        ]
    }
    """
    setup_style()
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    
    # X aralığı
    x_range = graph_data.get('x_range', [-5, 5])
    x = np.linspace(x_range[0], x_range[1], 500)
    
    # Ana fonksiyon
    expr = graph_data.get('function', '')
    y = safe_function_eval(expr, x)
    
    if y is None:
        plt.close(fig)
        return None
    
    ax.plot(x, y, color='#6366f1', linewidth=2.5, 
            label=f'f(x) = {expr.replace("**", "^")}')
    
    # Kritik noktalar
    points = graph_data.get('points', [])
    color_map = {
        'min': '#10b981', 'minimum': '#10b981', 'green': '#10b981',
        'max': '#dc2626', 'maximum': '#dc2626', 'red': '#dc2626',
        'inflection': '#f59e0b', 'eyer': '#f59e0b', 'yellow': '#f59e0b'
    }
    
    for point in points:
        px = point.get('x')
        py = point.get('y')
        label = point.get('label', '')
        color_key = (point.get('color') or label or 'blue').lower()
        color = color_map.get(color_key, '#6366f1')
        
        if px is not None and py is not None:
            ax.plot(px, py, 'o', color=color, markersize=11,
                    markeredgecolor='white', markeredgewidth=2, zorder=5)
            if label:
                ax.annotate(f'{label}\n({px}, {py})',
                            xy=(px, py), xytext=(10, 10),
                            textcoords='offset points', fontsize=10,
                            bbox=dict(boxstyle='round,pad=0.4',
                                      facecolor='#fef3c7',
                                      edgecolor=color, alpha=0.95))
    
    # Eksenler
    ax.axhline(y=0, color='#374151', linewidth=0.8, alpha=0.7)
    ax.axvline(x=0, color='#374151', linewidth=0.8, alpha=0.7)
    
    title = graph_data.get('title', 'Kritik Noktalar')
    ax.set_title(title, pad=15)
    
    ax.set_xlabel('x', fontsize=12, style='italic')
    ax.set_ylabel('y', fontsize=12, style='italic')
    ax.legend(loc='best', fontsize=10)
    ax.margins(x=0.02, y=0.1)
    
    return save_to_svg(fig)


# ═══════════════════════════════════════════
# ANA ÜRETİM FONKSIYONU
# ═══════════════════════════════════════════

def generate_graph(graph_data):
    """
    Verilen graph_data'ya göre uygun grafik üretir.
    
    Args:
        graph_data: dict — AI tarafından üretilen yapısal grafik verisi
    
    Returns:
        str — SVG kodu veya None
    """
    if not graph_data or not isinstance(graph_data, dict):
        graph_stats['no_data'] += 1
        return None
    
    graph_type = graph_data.get('graph_type', 'function').lower()
    
    print(f"🎨 Grafik üretiliyor: tip={graph_type}")
    
    try:
        if graph_type == 'function':
            svg = create_function_plot(graph_data)
        elif graph_type == 'integral':
            svg = create_integral_plot(graph_data)
        elif graph_type == 'derivative':
            svg = create_derivative_plot(graph_data)
        elif graph_type in ('critical_points', 'points'):
            svg = create_points_plot(graph_data)
        else:
            # Bilinmeyen tip için function ile dene
            print(f"⚠️ Bilinmeyen grafik tipi: {graph_type}, function denenecek")
            svg = create_function_plot(graph_data)
        
        if svg:
            graph_stats[f'{graph_type}_success'] += 1
            print(f"✅ Grafik başarıyla üretildi ({graph_type})")
        else:
            graph_stats[f'{graph_type}_failed'] += 1
            print(f"❌ Grafik üretilemedi ({graph_type})")
        
        return svg
    
    except Exception as e:
        graph_stats[f'{graph_type}_error'] += 1
        print(f"❌ Grafik üretim hatası ({graph_type}): {e}")
        return None


# ═══════════════════════════════════════════
# SVG SAVE
# ═══════════════════════════════════════════

def save_to_svg(fig):
    """Matplotlib figürünü SVG string'e çevirir."""
    try:
        buffer = BytesIO()
        fig.savefig(buffer, format='svg', bbox_inches='tight',
                    pad_inches=0.2, transparent=False)
        plt.close(fig)
        
        svg_data = buffer.getvalue().decode('utf-8')
        buffer.close()
        
        # XML declaration'ı temizle (HTML'e gömeceğiz)
        svg_data = re.sub(r'<\?xml[^>]+\?>', '', svg_data)
        svg_data = re.sub(r'<!DOCTYPE[^>]+>', '', svg_data)
        
        # Boyutu responsive yap
        svg_data = re.sub(
            r'<svg ([^>]*) width="[^"]+" height="[^"]+"',
            r'<svg \1 width="100%" height="auto" style="max-width:700px"',
            svg_data,
            count=1
        )
        
        return svg_data.strip()
    
    except Exception as e:
        print(f"❌ SVG kaydetme hatası: {e}")
        plt.close(fig)
        return None


def get_graph_stats():
    """Grafik üretim istatistiklerini döner."""
    return dict(graph_stats)


# ═══════════════════════════════════════════
# SELF TEST
# ═══════════════════════════════════════════

def run_self_test():
    """Modülü test eder."""
    print("\n═══ EduScan Graph Generator Self-Test ═══\n")
    
    tests = [
        {
            'name': 'Basit fonksiyon',
            'data': {
                'graph_type': 'function',
                'functions': [
                    {'expr': 'x**2', 'label': 'f(x) = x²'}
                ],
                'x_range': [-3, 3],
                'title': 'Parabol'
            }
        },
        {
            'name': 'İki fonksiyon kesişim',
            'data': {
                'graph_type': 'function',
                'functions': [
                    {'expr': 'x**2', 'label': 'f(x) = x²', 'color': 'blue'},
                    {'expr': 'x + 2', 'label': 'g(x) = x+2', 'color': 'red'}
                ],
                'x_range': [-3, 3],
                'title': 'Kesişim Noktaları',
                'annotations': [
                    {'x': 2, 'y': 4, 'text': 'Kesişim'},
                    {'x': -1, 'y': 1, 'text': 'Kesişim'}
                ]
            }
        },
        {
            'name': 'İntegral alanı',
            'data': {
                'graph_type': 'integral',
                'function': 'x**2',
                'integral_range': [0, 2],
                'x_range': [-1, 3],
                'title': 'Belirli İntegral',
                'show_value': '∫₀² x² dx = 8/3 ≈ 2.67'
            }
        },
        {
            'name': 'Türev/Teğet',
            'data': {
                'graph_type': 'derivative',
                'function': 'x**2',
                'derivative': '2*x',
                'point': 1,
                'x_range': [-3, 3],
                'title': 'x=1 Noktasında Teğet'
            }
        },
        {
            'name': 'Kritik noktalar',
            'data': {
                'graph_type': 'critical_points',
                'function': 'x**3 - 3*x',
                'x_range': [-3, 3],
                'points': [
                    {'x': 1, 'y': -2, 'label': 'Min', 'color': 'green'},
                    {'x': -1, 'y': 2, 'label': 'Max', 'color': 'red'}
                ]
            }
        }
    ]
    
    for test in tests:
        print(f"📊 Test: {test['name']}")
        svg = generate_graph(test['data'])
        if svg:
            print(f"   ✅ SVG üretildi ({len(svg)} karakter)")
        else:
            print(f"   ❌ Üretilemedi")
        print()


if __name__ == '__main__':
    run_self_test()