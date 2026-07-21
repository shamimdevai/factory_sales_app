"""
ReportLab's built-in fonts (Helvetica) have no Bengali glyphs, so the Taka
sign (৳) and any other Bengali text prints as a missing-glyph box (■). This
registers a real Unicode font once per process, so every PDF paragraph and
canvas.drawString call can render Bengali correctly.

Resolution order:
1. A font you bundle yourself at assets/fonts/NotoSansBengali-*.ttf (works on
   any OS, and is what PyInstaller will bundle into the .exe).
2. Windows' built-in "Nirmala UI" (C:\\Windows\\Fonts\\Nirmala.ttf), which ships
   with every Windows 10/11 install and already supports Bengali.
3. Falls back to Helvetica (glyph box will reappear) only if neither exists.
"""
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from src.utils.asset_utils import get_asset_path

_FONTS_REGISTERED = False
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def register_unicode_fonts():
    global _FONTS_REGISTERED, FONT_REGULAR, FONT_BOLD
    if _FONTS_REGISTERED:
        return FONT_REGULAR, FONT_BOLD

    candidates = [
        (get_asset_path("assets/fonts/NotoSansBengali-Regular.ttf"),
         get_asset_path("assets/fonts/NotoSansBengali-Bold.ttf")),
        (r"C:\Windows\Fonts\Nirmala.ttf", r"C:\Windows\Fonts\NirmalaB.ttf"),
    ]

    for regular_path, bold_path in candidates:
        if os.path.exists(regular_path):
            try:
                pdfmetrics.registerFont(TTFont("UnicodeFont", regular_path))
                pdfmetrics.registerFont(
                    TTFont("UnicodeFont-Bold", bold_path if os.path.exists(bold_path) else regular_path)
                )
                FONT_REGULAR, FONT_BOLD = "UnicodeFont", "UnicodeFont-Bold"
                break
            except Exception as e:
                print(f"[PDF Engine Warning]: Failed to register font '{regular_path}': {e}")

    _FONTS_REGISTERED = True
    return FONT_REGULAR, FONT_BOLD