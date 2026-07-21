"""
PDF invoice appearance. Edit these per company deployment — pdf_generator.py
never needs to change. Colors: "#rrggbb" or ("#rrggbb", alpha 0-1) for transparency.
"""
COMPANY_INFO_BG   = ("#3498db", 0.08)
CUSTOMER_INFO_BG  = ("#2ecc71", 0.08)
ITEMS_HEADER_BG   = "#2c3e50"
ITEMS_ALT_ROW_BG  = ("#2c3e50", 0.04)
PAYMENT_BLOCK_BG  = ("#9b59b6", 0.10)
FOOTER_BG         = ("#2c3e50", 0.06)

def hex_with_alpha(value):
    from reportlab.lib import colors
    if isinstance(value, tuple):
        hexcode, alpha = value
        c = colors.HexColor(hexcode)
        return colors.Color(c.red, c.green, c.blue, alpha=alpha)
    return colors.HexColor(value)