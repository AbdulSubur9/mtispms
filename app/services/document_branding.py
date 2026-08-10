"""
Shared branding layer for every generated PDF (receipts, admission forms,
attendance reports, exam result sheets, financial reports, ...).

Instead of every PDF generator duplicating "draw the logo, school name,
address" boilerplate, they all call `branded_header()` / `branded_footer()`
here and get the SAME look, driven by whichever school owns the document -
never hard-coded. Add a new document type by importing these two functions,
not by copy-pasting header code again.
"""
import os
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_styles = getSampleStyleSheet()

# ---------------------------------------------------------------------------
# Arabic/bilingual label support.
#
# ReportLab's built-in fonts (Helvetica, Times, ...) do not contain Arabic
# glyphs at all - text would render as blank boxes, which is worse than not
# showing it. Proper Arabic rendering also needs shaping/bidi reordering
# (the "arabic-reshaper" + "python-bidi" packages) on top of a Unicode font.
#
# This environment doesn't have internet access to fetch a font file or
# install those packages, so bilingual labels degrade GRACEFULLY: if a
# Unicode Arabic-capable TTF is present at ARABIC_FONT_PATH, it's registered
# and used; otherwise Arabic labels are simply omitted (English-only) rather
# than rendering garbled/blank glyphs. See README/CHANGELOG for the exact
# steps to enable full bilingual output.
# ---------------------------------------------------------------------------
ARABIC_FONT_NAME = "NotoNaskhArabic"
ARABIC_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "fonts", "NotoNaskhArabic-Regular.ttf")
_arabic_font_registered = None  # tri-state cache: None = not checked yet


def arabic_font_available():
    """Registers the bundled Arabic font on first use, if present. Returns
    True/False and caches the result so we only touch the filesystem once."""
    global _arabic_font_registered
    if _arabic_font_registered is None:
        if os.path.isfile(ARABIC_FONT_PATH):
            try:
                pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, ARABIC_FONT_PATH))
                _arabic_font_registered = True
            except Exception:
                _arabic_font_registered = False
        else:
            _arabic_font_registered = False
    return _arabic_font_registered


def bilingual_label(english, arabic):
    """Returns "English / <Arabic script>" if a bilingual font is bundled,
    otherwise just "English" - never renders Arabic text with a font that
    can't display it. NOTE: even when shown, this does not apply proper
    bidi/shaping reordering, so visual correctness of the Arabic text isn't
    guaranteed until arabic-reshaper + python-bidi are added - see the
    module docstring."""
    if arabic_font_available():
        return f"{english} / {arabic}"
    return english

SCHOOL_NAME_STYLE = ParagraphStyle(
    "BrandSchoolName", parent=_styles["Heading1"], fontSize=17, alignment=1, spaceAfter=2,
    textColor=colors.HexColor("#1b4332"),
)
SCHOOL_SUBLINE_STYLE = ParagraphStyle(
    "BrandSubline", parent=_styles["Normal"], fontSize=9, alignment=1, textColor=colors.grey, spaceAfter=1,
)
DOC_TITLE_STYLE = ParagraphStyle(
    "BrandDocTitle", parent=_styles["Heading2"], fontSize=13, alignment=1, spaceBefore=8, spaceAfter=10,
    textColor=colors.HexColor("#2d6a4f"),
)
FOOTER_STYLE = ParagraphStyle(
    "BrandFooter", parent=_styles["Normal"], fontSize=8, alignment=1, textColor=colors.grey,
)


def _logo_path(school):
    """Resolve the school's logo to a real filesystem path ReportLab can
    open, or None if there isn't one / it can't be found. PDF generation
    needs an actual file (or file-like object), not a URL - this only
    works with the local storage backend; a future object-storage backend
    would need to download the logo to a temp file first."""
    if not school or not school.logo:
        return None
    try:
        from flask import current_app
        path = os.path.join(current_app.static_folder, school.logo)
        return path if os.path.isfile(path) else None
    except Exception:
        return None


def branded_header(school, document_title, subtitle=None, logo_max_height=22 * mm):
    """Returns a list of flowables: logo (if set) + school name + contact
    line + optional custom header text + document title + a rule. Prepend
    this to any ReportLab `elements` list."""
    elements = []

    logo_path = _logo_path(school)
    if logo_path:
        try:
            img = Image(logo_path)
            # Scale down proportionally if it's larger than our max height
            if img.drawHeight > logo_max_height:
                ratio = logo_max_height / img.drawHeight
                img.drawHeight = logo_max_height
                img.drawWidth *= ratio
            img.hAlign = "CENTER"
            elements.append(img)
            elements.append(Spacer(1, 4))
        except Exception:
            pass  # a corrupt/unreadable logo file should never break document generation

    elements.append(Paragraph(school.name if school else "Madrasah", SCHOOL_NAME_STYLE))

    contact_bits = []
    if school:
        if school.address:
            contact_bits.append(school.address)
        if school.phone:
            contact_bits.append(school.phone)
        if school.email:
            contact_bits.append(school.email)
    if contact_bits:
        elements.append(Paragraph(" | ".join(contact_bits), SCHOOL_SUBLINE_STYLE))

    if school and school.motto:
        elements.append(Paragraph(f'"{school.motto}"', SCHOOL_SUBLINE_STYLE))
    if school and school.document_header_text:
        elements.append(Paragraph(school.document_header_text, SCHOOL_SUBLINE_STYLE))

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1b4332"), spaceBefore=6, spaceAfter=6))
    elements.append(Paragraph(document_title, DOC_TITLE_STYLE))
    if subtitle:
        elements.append(Paragraph(subtitle, SCHOOL_SUBLINE_STYLE))
        elements.append(Spacer(1, 6))

    return elements


def branded_footer(school):
    """A short footer paragraph - append near the end of any document."""
    bits = []
    if school and school.document_footer_text:
        bits.append(school.document_footer_text)
    bits.append("Generated by MT-ISPMS")
    return [
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceBefore=4, spaceAfter=4),
        Paragraph(" | ".join(bits), FOOTER_STYLE),
    ]


def signature_block(labels):
    """A row of signature lines, e.g. signature_block(["Parent/Guardian
    Signature", "Admin Signature"]). Returns a single Table flowable."""
    cell = "_____________________________"
    row1 = [cell for _ in labels]
    row2 = list(labels)
    t = Table([row1, row2], colWidths=[180] * len(labels))
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return t
