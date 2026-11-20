# pdf_generator.py
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
import os
import traceback
import arabic_reshaper
from bidi.algorithm import get_display
from datetime import datetime

FONT_NAME = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

FONT_PATHS = [
    ('C:/Windows/Fonts/tahoma.ttf', 'ArabicFont'),
    ('C:/Windows/Fonts/tahomabd.ttf', 'ArabicFontBold'),
    ('/system/fonts/NotoNaskhArabic-Regular.ttf', 'ArabicFont'),
    ('/system/fonts/NotoNaskhArabic-Bold.ttf', 'ArabicFontBold'),
    ('/system/fonts/DroidSansArabic.ttf', 'ArabicFont'),
]

for path, name in FONT_PATHS:
    try:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            if 'Bold' in name:
                if FONT_BOLD == 'Helvetica-Bold': FONT_BOLD = name
            else:
                if FONT_NAME == 'Helvetica': FONT_NAME = name
    except Exception as e:
        pass

if FONT_BOLD == 'Helvetica-Bold': FONT_BOLD = FONT_NAME

def ar_pdf(text):
    if not text: return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

LAYOUTS = {
    4:  (2, 2, 0.80),  # 4 كروت = QR ضخم جداً
    6:  (2, 3, 0.75),
    9:  (3, 3, 0.72),
    12: (3, 4, 0.70),
    16: (4, 4, 0.68),
    20: (4, 5, 0.66),
    25: (5, 5, 0.65),
    30: (5, 6, 0.62),
}

def _get_layout(cards_per_page):
    cards_per_page = max(1, int(cards_per_page))
    if cards_per_page in LAYOUTS:
        return LAYOUTS[cards_per_page]
    import math
    cols = math.ceil(math.sqrt(cards_per_page))
    rows = math.ceil(cards_per_page / cols)
    ratio = 0.78 if cards_per_page <= 6 else (0.70 if cards_per_page <= 12 else (0.66 if cards_per_page <= 20 else 0.62))
    return (cols, rows, ratio)

def generate_qr_pdf(students, cards_per_page=9, output_dir=None, paid_ids=None):
    try:
        if paid_ids is None: paid_ids = set()
        if output_dir is None:
            candidates = ["/storage/emulated/0/Download", os.path.expanduser("~/storage/downloads"), os.path.expanduser("~")]
            for c in candidates:
                try:
                    os.makedirs(c, exist_ok=True)
                    test = os.path.join(c, ".wtest")
                    open(test, "w").close()
                    os.remove(test)
                    output_dir = c
                    break
                except Exception:
                    continue
            if output_dir is None: output_dir = os.path.expanduser("~")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(output_dir, f"walaa_cards_{timestamp}.pdf")

        cols, rows, qr_ratio = _get_layout(cards_per_page)

        by_grade = {}
        for s in students:
            by_grade.setdefault(s['year'], []).append(s)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        margin_x = 8 * mm
        margin_y = 8 * mm
        header_h = 14 * mm
        gap = 3 * mm

        card_w = (width - 2 * margin_x - gap * (cols - 1)) / cols
        card_h = (height - 2 * margin_y - header_h - gap * (rows - 1)) / rows
        qr_size = min(card_w, card_h) * qr_ratio

        for grade in sorted(by_grade.keys()):
            grade_list = by_grade[grade]
            paid_students = sorted([s for s in grade_list if s['id'] in paid_ids], key=lambda x: x['name'])
            unpaid_students = sorted([s for s in grade_list if s['id'] not in paid_ids], key=lambda x: x['name'])
            ordered = paid_students + unpaid_students
            pages = [ordered[i:i + cards_per_page] for i in range(0, len(ordered), cards_per_page)]

            for page_idx, chunk in enumerate(pages):
                c.setFillColorRGB(0.925, 0.282, 0.600)
                c.rect(margin_x, height - margin_y - header_h, width - 2 * margin_x, header_h, fill=1, stroke=0)
                c.setFillColorRGB(1, 1, 1)
                c.setFont(FONT_BOLD, 13)
                title = f"{grade} — {len(paid_students)}✅ / {len(unpaid_students)}❌"
                if len(pages) > 1: title += f"  ({page_idx + 1}/{len(pages)})"
                c.drawCentredString(width / 2, height - margin_y - header_h + 5 * mm, ar_pdf(title))

                for i, s in enumerate(chunk):
                    row = i // cols
                    col = i % cols
                    x = margin_x + col * (card_w + gap)
                    y = height - margin_y - header_h - (row + 1) * card_h - row * gap
                    is_paid = s['id'] in paid_ids

                    c.setStrokeColorRGB(0.063, 0.725, 0.506) if is_paid else c.setStrokeColorRGB(0.937, 0.267, 0.267)
                    c.setLineWidth(1.2)
                    c.rect(x + 1, y + 1, card_w - 2, card_h - 2)

                    if is_paid: c.setFillColorRGB(0.063, 0.725, 0.506)
                    else: c.setFillColorRGB(0.937, 0.267, 0.267)
                    c.rect(x + 1, y + card_h - 2.5 * mm, card_w - 2, 2.5 * mm, fill=1, stroke=0)

                    payload = f'{{"code":"{s["code"]}","name":"{s["name"]}","year":"{s["year"]}","fee":{s["fee"]}}}'
                    qr_widget = qr.QrCodeWidget(payload)
                    qr_widget.barWidth, qr_widget.barHeight = qr_size, qr_size
                    bounds = qr_widget.getBounds()
                    d = Drawing(qr_size, qr_size, transform=[qr_size/(bounds[2]-bounds[0]), 0, 0, qr_size/(bounds[3]-bounds[1]), 0, 0])
                    d.add(qr_widget)
                    renderPDF.draw(d, c, x + (card_w - qr_size) / 2, y + card_h - qr_size - 4 * mm)

                    c.setFillColorRGB(0, 0, 0)
                    c.setFont(FONT_BOLD, 9 if cards_per_page <= 12 else (7 if cards_per_page <= 20 else 6))
                    c.drawCentredString(x + card_w / 2, y + 8 * mm, ar_pdf(s['name']))

                    c.setFont(FONT_NAME, 6)
                    c.setFillColorRGB(0.4, 0.4, 0.4)
                    c.drawCentredString(x + card_w / 2, y + 4.5 * mm, s['code'])

                    c.setFont(FONT_NAME, 5.5)
                    c.setFillColorRGB(0.063, 0.725, 0.506) if is_paid else c.setFillColorRGB(0.937, 0.267, 0.267)
                    c.drawCentredString(x + card_w / 2, y + 2 * mm, ar_pdf("دفع" if is_paid else "لم يدفع"))

                c.showPage()

        c.save()
        return (True, pdf_path)
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")
