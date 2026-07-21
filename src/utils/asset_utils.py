import sys, os

def get_asset_path(relative_path: str) -> str:
    """Resolves paths for both dev and PyInstaller .exe builds."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_path, relative_path)