"""
Central UI theme — background/card/border/accent colors, AND responsive layout
behavior (table column sizing, sidebar scaling) shared across every page.

Deliberately separate from src/config/company_config.py:
  - company_config.py = CLIENT branding (name, logo, status colors) — swap per client
  - theme.py           = APP look-and-feel + responsive behavior — change once,
                          applies everywhere, independent of which client's data is loaded

To re-theme the whole app, edit the constants below. To change how tables/sidebar
respond to window resizing, edit configure_responsive_table() / the SIDEBAR_*
constants below. Nothing else needs to change.
"""
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QCheckBox, QStyle, QStyleOptionButton
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QRectF, QPointF, QObject, QEvent

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


# --- Frozen/footer summary row (e.g. Customer Purchase Summary TOTAL row) ---
TOTALS_ROW_BACKGROUND = "#E8F4F8"  # pale blue-gray -- distinct from PAGE_BACKGROUND's mint tint


# --- Customer Status (tier) badge colors ---
# Assigned by RANK POSITION (highest tier first = index 0), not by tier name --
# your top-ranked tier always gets the first color here regardless of what
# you've named it in Settings. Add more colors if you define more than 6
# tiers; extras beyond the list fall back to ACCENT. Customers with no
# qualifying tier ("Standard") use STATUS_STANDARD_COLOR. Used by both the
# Customers page and the Invoice Terminal's customer picker -- change it once
# here and both pick it up automatically.
STATUS_TIER_PALETTE = ["#b8860b", "#95a5a6", "#cd7f32", "#1abc9c", "#3498db", "#9b59b6"]
STATUS_STANDARD_COLOR = TEXT_MUTED


# --- Responsive table behavior ---
TABLE_MIN_SECTION_SIZE = 60  # global floor (px) for any column -- below this, horizontal
                              # scrolling kicks in rather than squeezing text unreadably

# --- Digital signature storage ceiling (Global Development Rule #4: signatures
# are always resized to fit this exact box and stored as PNG bytes, never as
# file paths). Single source of truth -- profile_view.py's SignatureEditorDialog
# reads these instead of hardcoding 200/80.
SIGNATURE_MAX_WIDTH = 200
SIGNATURE_MAX_HEIGHT = 80

# --- Sidebar sizing -- change SIDEBAR_WIDTH and/or SIDEBAR_LOGO_WIDTH_RATIO
# here and both the panel and the logo stay proportionate to each other,
# instead of being two independent numbers you have to re-tune together. ---
SIDEBAR_WIDTH = 240              # fixed sidebar panel width (px)
SIDEBAR_LOGO_WIDTH_RATIO = 0.55  # logo width as a fraction of SIDEBAR_WIDTH
SIDEBAR_BRAND_FONT_SIZE = 16


# --- Responsive page-header buttons (e.g. "+ Add Customer" collapsing to icon-only) ---
HEADER_BUTTON_COMPACT_BREAKPOINT = 650  # container width (px) below which registered buttons go icon-only


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


class TickCheckBox(QCheckBox):
    """A QCheckBox that paints its own indicator box (black border + an actual
    checkmark when checked) with QPainter, layered on top of Qt's normal
    rendering. This exists because of a genuine Qt stylesheet limitation: as
    soon as any QSS rule targets ::indicator, Qt stops drawing its own native
    checkmark glyph entirely for every state -- so a visible custom border and
    a visible tick mark can't both come from QSS alone. This needs zero
    external assets/files and no stylesheet at all for the indicator. Use this
    in place of plain QCheckBox everywhere in the app (Rule #9 -- one place
    owns checkbox appearance)."""

    def paintEvent(self, event):
        # 1. Let Qt paint everything normally first -- label text, focus
        # rect, and its own (too-faint-to-see) native indicator box.
        super().paintEvent(event)

        # 2. Paint our own indicator box directly on top, in the same rect
        # Qt just used, fully covering the faint native one underneath.
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        indicator_rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, opt, self
        )
        box = QRectF(indicator_rect).adjusted(1, 1, -1, -1)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.setBrush(QColor(CARD_BACKGROUND))
        painter.drawRoundedRect(box, 3, 3)

        if self.isChecked():
            pen = QPen(QColor(ACCENT), 2.3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            x, y, w, h = box.x(), box.y(), box.width(), box.height()
            painter.drawLine(QPointF(x + w * 0.20, y + h * 0.55), QPointF(x + w * 0.42, y + h * 0.78))
            painter.drawLine(QPointF(x + w * 0.42, y + h * 0.78), QPointF(x + w * 0.82, y + h * 0.22))

        painter.end()


def sidebar_logo_size() -> int:
    """Logo pixmap size (px, square) — always SIDEBAR_LOGO_WIDTH_RATIO of
    SIDEBAR_WIDTH, so changing either constant above keeps the logo
    proportionate to the panel automatically, no manual re-tuning needed."""
    return int(SIDEBAR_WIDTH * SIDEBAR_LOGO_WIDTH_RATIO)


def totals_row_style() -> str:
    """Frozen/footer totals-row table styling — pale accent-tinted band with a
    top accent border. Used by any page showing a pinned summary row below a
    scrollable data table (e.g. Customer Purchase Summary)."""
    return f"QTableWidget {{ background: {TOTALS_ROW_BACKGROUND}; border: none; border-top: 2px solid {ACCENT}; }}"


def configure_responsive_table(table: QTableWidget, columns: list, min_section_size: int = TABLE_MIN_SECTION_SIZE):
    """
    Makes a QTableWidget's columns responsive to window resizing instead of
    fixed pixel widths that just trigger horizontal scrolling.

    columns: ordered list of (width_px, mode) tuples, one per column, in the
    table's actual column order:
      - width_px: initial/preferred width. For "stretch" columns this also
        establishes the RATIO between columns -- Qt's Stretch resize mode
        preserves relative proportions between stretch columns as the table
        resizes (using each column's size at the moment Stretch is applied
        as the baseline), so setting these widths first and switching modes
        second is what makes proportional (not equal-split) responsiveness work.
      - mode: "stretch" (grows/shrinks with the window, keeping proportions)
        or "fixed" (stays exactly width_px regardless of resizing -- use for
        narrow action/icon columns that shouldn't grow).

    Also hides the default row-number column (vertical header) and applies
    the shared minimum column width floor, so every table in the app that
    goes through this helper behaves consistently without each caller having
    to remember every individual setting.

    IMPORTANT CALL ORDER: call this BEFORE setHorizontalHeaderLabels(). This
    function sets the table's column count; setHorizontalHeaderLabels() on a
    table that still has 0 columns silently discards the labels (Qt only
    attaches header text to columns that already exist).
    """
    table.setColumnCount(len(columns))
    header = table.horizontalHeader()
    header.setMinimumSectionSize(min_section_size)

    # Pass 1: set explicit pixel widths for every column while resize mode is
    # still Interactive (the QTableWidget default) -- this establishes the
    # baseline proportions Stretch mode will preserve once applied below.
    for col, (width, _mode) in enumerate(columns):
        table.setColumnWidth(col, width)

    # Pass 2: apply the actual resize modes now that baseline widths are set.
    for col, (_width, mode) in enumerate(columns):
        resize_mode = QHeaderView.ResizeMode.Fixed if mode == "fixed" else QHeaderView.ResizeMode.Stretch
        header.setSectionResizeMode(col, resize_mode)

    table.verticalHeader().setVisible(False)  # no default row-number column, app-wide

class _ResponsiveButtonFilter(QObject):
    """Watches a container widget's resize events and swaps each registered
    button between its full label and a compact (icon-only) label once the
    container drops below a width breakpoint -- keeps header-style button
    rows (page titles + action buttons) from silently overflowing/getting
    clipped on narrow windows instead of actually adapting to the space."""

    def __init__(self, container, button_specs, breakpoint_width):
        super().__init__(container)  # Qt-parented to the container -> stays alive with it
        self._container = container
        self._button_specs = button_specs  # list of (button, full_text, compact_text)
        self._breakpoint = breakpoint_width
        self._compact = None  # tracks current state so we don't call setText redundantly
        container.installEventFilter(self)
        self._apply(container.width())

    def eventFilter(self, obj, event):
        if obj is self._container and event.type() == QEvent.Type.Resize:
            self._apply(obj.width())
        return False

    def _apply(self, width: int):
        compact = width < self._breakpoint
        if compact == self._compact:
            return
        self._compact = compact
        for button, full_text, compact_text in self._button_specs:
            button.setText(compact_text if compact else full_text)
            # Full label is hidden in compact mode -- tooltip is the only way
            # to see what the icon-only button actually does, so show it only
            # when needed (no point showing a tooltip when the text is already visible).
            button.setToolTip(full_text if compact else "")


def install_responsive_buttons(container, button_specs: list, breakpoint_width: int = HEADER_BUTTON_COMPACT_BREAKPOINT):
    """Registers (button, full_text, compact_text) tuples on a container
    widget (typically a page's top-level QWidget) so those buttons collapse
    to their compact/icon-only label once the container's width drops below
    breakpoint_width, and restore automatically once it grows back.

    Usage:
        self._header_filter = theme.install_responsive_buttons(self, [
            (self.btn_refresh, "🔄 Refresh", "🔄"),
            (self.btn_add, "+ Add Customer", "+"),
        ])

    Keep the returned object referenced (e.g. assign to self.<name> as shown)
    for as long as the container exists."""
    return _ResponsiveButtonFilter(container, button_specs, breakpoint_width)