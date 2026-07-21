import os
from src.utils.asset_utils import get_asset_path

COMPANY_NAME = "Chashi-Bondhu Vermi-Compost Ltd."
COMPANY_ADDRESS = "Zothohari, Mohadevpur, Naogaon, Bangladesh"
COMPANY_EMAIL = "chashibondhu4@gmail.com"
COMPANY_PHONE = "+8801786642237"
COMPANY_WHATSAPP = "+8801786642237"
COMPANY_WEBSITE = ""        # e.g. "www.chashibondhu.com"
COMPANY_FACEBOOK = "facebook.com/chashibondhubd"       # e.g. "facebook.com/chashibondhubd"

CURRENCY_SYMBOL = "৳"

# Drop your real files here: assets/logo.png (square PNG, transparent bg(background works best, ~512×512))
# and assets/app_icon.ico (for the Windows exe/desktop icon)
_logo_file = get_asset_path("assets/logo.png")
COMPANY_LOGO_PATH = _logo_file if os.path.exists(_logo_file) and os.path.getsize(_logo_file) > 0 else None

_icon_file = get_asset_path("assets/app_icon.ico")
APP_ICON_PATH = _icon_file if os.path.exists(_icon_file) and os.path.getsize(_icon_file) > 0 else COMPANY_LOGO_PATH

# Status color scheme — shared by the PyQt UI and the PDF engine
STATUS_COLORS = {
    "paid": "#1e8449",
    "due": "#c0392b",
    "unpaid": "#c0392b",
    "partial due": "#2471a3",
    "partial": "#2471a3",
}
DEFAULT_STATUS_COLOR = "#2c3e50"

def resolve_status_color(status: str) -> str:
    key = (status or "").strip().lower()
    if "partial" in key:
        return STATUS_COLORS["partial due"]
    if "due" in key or "unpaid" in key:
        return STATUS_COLORS["due"]
    if "paid" in key:
        return STATUS_COLORS["paid"]
    return DEFAULT_STATUS_COLOR