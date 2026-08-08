"""
Central UI theme — background/card/border/accent colors shared across every page.

Deliberately separate from src/config/company_config.py:
  - company_config.py = CLIENT branding (name, logo, status colors) — swap per client
  - theme.py           = APP look-and-feel (backgrounds, accents) — change once, applies
                          everywhere, independent of which client's data is loaded

To re-theme the whole app, edit the constants below. Nothing else needs to change.
"""

# --- Page / layout backgrounds ---
PAGE_BACKGROUND = "#EEF6F0"      # subtle mint-green tint for every page's content area
SIDEBAR_BACKGROUND = "#2C3E50"   # kept navy per client preference (not themed green)
SIDEBAR_HOVER = "#34495E"
CARD_BACKGROUND = "#FFFFFF"      # cards/frames/tables stay white for contrast + readability
BORDER_COLOR = "#CBD5E1"

# --- Brand accent (buttons, active nav, selection highlight) ---
ACCENT = "#1ABC9C"
ACCENT_DARK = "#16A085"

# --- Text (Drop-Down Menu) ---
TEXT_PRIMARY = "#2C3E50"
TEXT_MUTED = "#7F8C8D"


def card_frame_style() -> str:
    """Standard white card/frame with border — used throughout for content boxes."""
    return f"QFrame {{ background-color: {CARD_BACKGROUND}; border-radius: 6px; border: 1px solid {BORDER_COLOR}; }}"


def input_style(widget_selector: str = "QLineEdit") -> str:
    """Standard bordered input field style, parametrized by widget type
    (QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox, etc.).

    If "QComboBox" appears anywhere in widget_selector, the dropdown popup
    styling (combobox_dropdown_style()) is automatically appended too — so
    every combobox in the app gets working hover/selection text color by
    default, without each caller having to remember to add it separately."""
    base = (f"{widget_selector} {{ padding: 5px; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: 4px; background: {CARD_BACKGROUND}; color: {TEXT_PRIMARY}; }}")
    if "QComboBox" in widget_selector:
        base += combobox_dropdown_style()
    return base


def combobox_dropdown_style() -> str:
    """The QAbstractItemView popup portion of a QComboBox, themed with the accent color."""
    return f"""
        QComboBox QAbstractItemView {{
            background-color: {CARD_BACKGROUND};
            color: {TEXT_PRIMARY};
            selection-background-color: {ACCENT};
            selection-color: {CARD_BACKGROUND};
            outline: none;
            padding: 4px;
        }}
    """