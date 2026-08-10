from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QTabWidget,
    QFormLayout, QFrame, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from src.config import company_config as cfg
from src.config import theme

# --- Local one-off semantic button colors (per Rule 9 -- not centralized) ---
_EDIT_BTN = "QPushButton { background-color: #3498db; color: white; font-size: 11px; max-width: 28px; border-radius: 3px; } QPushButton:hover { background-color: #2980b9; }"
_LEDGER_BTN = "QPushButton { background-color: #8e44ad; color: white; font-size: 11px; max-width: 28px; border-radius: 3px; } QPushButton:hover { background-color: #6c3483; }"
_SAVE_BTN = "QPushButton { background-color: #27ae60; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #219653; }"
_ADD_BTN = f"QPushButton {{ background-color: {theme.ACCENT}; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background-color: {theme.ACCENT_DARK}; }}"


class CustomerDialog(QDialog):
    """Add/Edit a Customer. Pure GUI -- no DB access; type choices are passed in
    fresh by the controller each time it's opened (Settings page may have
    added/removed types since this page last loaded)."""

    def __init__(self, parent, type_choices: list, name="", phone="", email="",
                 address="", current_type_id=None):
        super().__init__(parent)
        self.setWindowTitle("Customer")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        input_style = theme.input_style("QLineEdit")

        self.txt_name = QLineEdit(name)
        self.txt_name.setStyleSheet(input_style)
        form.addRow("Name *:", self.txt_name)

        self.txt_phone = QLineEdit(phone)
        self.txt_phone.setStyleSheet(input_style)
        form.addRow("Phone *:", self.txt_phone)

        self.txt_email = QLineEdit(email)
        self.txt_email.setStyleSheet(input_style)
        form.addRow("Email:", self.txt_email)

        self.txt_address = QLineEdit(address)
        self.txt_address.setStyleSheet(input_style)
        form.addRow("Address:", self.txt_address)

        self.combo_type = QComboBox()
        self.combo_type.addItem("(None)", None)
        selected_index = 0
        for i, t in enumerate(type_choices):
            self.combo_type.addItem(t["name"], t["id"])
            if current_type_id is not None and t["id"] == current_type_id:
                selected_index = i + 1
        self.combo_type.setCurrentIndex(selected_index)
        self.combo_type.setStyleSheet(theme.input_style("QComboBox"))
        form.addRow("Type:", self.combo_type)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Save")
        btn_ok.setStyleSheet(_SAVE_BTN)
        btn_ok.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _validate_and_accept(self):
        if not self.txt_name.text().strip() or not self.txt_phone.text().strip():
            QMessageBox.warning(self, "Missing Fields", "Name and Phone are required.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.txt_name.text().strip(),
            "phone": self.txt_phone.text().strip(),
            "email": self.txt_email.text().strip(),
            "address": self.txt_address.text().strip(),
            "customer_type_id": self.combo_type.currentData(),
        }


class CustomerView(QWidget):
    add_customer_requested = pyqtSignal()
    edit_customer_requested = pyqtSignal(int)      # customer id
    view_ledger_requested = pyqtSignal(int, str)  # (customer_id, customer_name) -- main_window wires
    # this to History Ledger + customer_id filter mode (cross-page nav lives
    # there, not in CustomerController, to keep controllers decoupled).
    refresh_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        # self.setMinimumWidth(950)

        # Full unfiltered datasets, kept so the search box can filter row
        # visibility locally without re-querying the DB on every keystroke.
        self._directory_rows = []
        self._pivot_rows = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        header_row = QHBoxLayout()
        title = QLabel("Customers")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_row.addWidget(title)
        header_row.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet(
            "QPushButton { background-color: #34495e; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2c3e50; }")
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        header_row.addWidget(self.btn_refresh)

        self.btn_add = QPushButton("+ Add Customer")
        self.btn_add.setStyleSheet(_ADD_BTN)
        self.btn_add.clicked.connect(self.add_customer_requested.emit)
        header_row.addWidget(self.btn_add)
        self.main_layout.addLayout(header_row)

        # Collapses to icon-only once this page gets too narrow for full
        # button text -- instead of silently overflowing/getting clipped.
        self._header_button_filter = theme.install_responsive_buttons(self, [
            (self.btn_refresh, "🔄 Refresh", "🔄"),
            (self.btn_add, "+ Add Customer", "+"),
        ])

        # Shared search box -- filters row visibility in whichever tab is active.
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or phone...")
        self.search_input.setStyleSheet(theme.input_style("QLineEdit"))
        self.search_input.textChanged.connect(self._apply_search_filter)
        search_row.addWidget(self.search_input)
        self.main_layout.addLayout(search_row)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {theme.BORDER_COLOR}; border-radius: 6px; background: {theme.CARD_BACKGROUND}; }}
            QTabBar::tab {{ padding: 8px 16px; margin-right: 2px; background: {theme.PAGE_BACKGROUND}; color: {theme.TEXT_PRIMARY}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
            QTabBar::tab:selected {{ background: {theme.ACCENT}; color: white; font-weight: bold; }}
        """)
        self.tabs.addTab(self._create_directory_tab(), "Customer Directory")
        self.tabs.addTab(self._create_pivot_tab(), "Purchase Summary")
        self.main_layout.addWidget(self.tabs)

    # ---------------- Directory Tab ----------------
    def _create_directory_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.table_directory = QTableWidget()
        theme.configure_responsive_table(self.table_directory, [
            (150, "stretch"), (120, "stretch"), (170, "stretch"),
            (110, "stretch"), (100, "stretch"), (70, "fixed"),
        ])
        self.table_directory.setHorizontalHeaderLabels(
            ["Name", "Phone", "Email", "Type", "Status", "Actions"])
        self.table_directory.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_directory.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_directory.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_directory.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_directory.setStyleSheet(
            f"QTableWidget {{ background: {theme.CARD_BACKGROUND}; border: none; }}")
        layout.addWidget(self.table_directory)
        return tab

    def populate_directory(self, rows: list):
        """rows: list of dicts: {id, name, phone, email, type_name, status_name, status_color}"""
        self._directory_rows = rows
        self.table_directory.setRowCount(len(rows))
        for row, c in enumerate(rows):
            self.table_directory.setItem(row, 0, QTableWidgetItem(c["name"]))
            self.table_directory.setItem(row, 1, QTableWidgetItem(c["phone"]))
            self.table_directory.setItem(row, 2, QTableWidgetItem(c["email"] or ""))
            self.table_directory.setItem(row, 3, QTableWidgetItem(c["type_name"] or "—"))

            status_item = QTableWidgetItem(c["status_name"])
            status_item.setForeground(QColor(c["status_color"]))
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_directory.setItem(row, 4, status_item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(3)
            btn_edit = QPushButton("✏️")
            btn_edit.setToolTip("Edit Customer")
            btn_edit.setStyleSheet(_EDIT_BTN)
            btn_edit.clicked.connect(lambda checked, cid=c["id"]: self.edit_customer_requested.emit(cid))
            btn_ledger = QPushButton("🧾")
            btn_ledger.setToolTip("View Invoice Ledger")
            btn_ledger.setStyleSheet(_LEDGER_BTN)
            btn_ledger.clicked.connect(
                lambda checked, cid=c["id"], cname=c["name"]: self.view_ledger_requested.emit(cid, cname))
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_ledger)
            self.table_directory.setCellWidget(row, 5, actions_widget)

        self._apply_search_filter(self.search_input.text())

    # ---------------- Pivot Tab ----------------
    def _create_pivot_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)  # footer sits flush against the main table, like a frozen row

        column_spec = [
            (150, "stretch"), (70, "stretch"), (110, "stretch"), (100, "stretch"),
            (100, "stretch"), (100, "stretch"), (120, "stretch"), (100, "stretch"),
            (90, "stretch"), (60, "fixed"),
        ]

        self.table_pivot = QTableWidget()
        theme.configure_responsive_table(self.table_pivot, column_spec)
        self.table_pivot.setHorizontalHeaderLabels([
            "Customer", "Invoices", "Discount","Grand Total", "Paid", "Due",
            "Last Purchase", "Compost (kg)", "Worms (kg)", "Actions"
        ])
        self.table_pivot.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_pivot.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_pivot.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_pivot.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_pivot.setStyleSheet(
            f"QTableWidget {{ background: {theme.CARD_BACKGROUND}; border: none; }}")
        layout.addWidget(self.table_pivot)

        # --- Frozen TOTAL footer: a second, 1-row table kept in sync with the
        # main table's LIVE (responsive) column widths and horizontal scroll
        # position, so it's always visible regardless of scroll position or
        # window size -- a plain QTableWidget can't natively "freeze" a row.
        # Its own columns stay Fixed and are driven purely by mirroring the
        # main table (rather than being independently responsive), avoiding
        # any rounding drift between two separately-stretched headers. ---
        self.table_pivot_totals = QTableWidget(1, 10)
        self.table_pivot_totals.horizontalHeader().setVisible(False)
        self.table_pivot_totals.verticalHeader().setVisible(False)
        for col, (width, _mode) in enumerate(column_spec):
            self.table_pivot_totals.setColumnWidth(col, width)
        self.table_pivot_totals.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_pivot_totals.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_pivot_totals.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_pivot_totals.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_pivot_totals.setFixedHeight(38)
        self.table_pivot_totals.setStyleSheet(theme.totals_row_style())
        layout.addWidget(self.table_pivot_totals)

        # Keep the footer's columns and horizontal scroll glued to the main table.
        self.table_pivot.horizontalHeader().sectionResized.connect(
            lambda col, old, new: self.table_pivot_totals.setColumnWidth(col, new))
        self.table_pivot.horizontalScrollBar().valueChanged.connect(
            self.table_pivot_totals.horizontalScrollBar().setValue)

        return tab

    def populate_pivot(self, rows: list, totals: dict):
        """rows: list of dicts: {id, name, invoices, discount, grand_total, paid,
        due, last_purchase, compost_kg, worms_kg}
        totals: dict of the same numeric keys, pre-summed across ALL customers --
        rendered in the separate frozen footer table (table_pivot_totals),
        always visible regardless of search filtering or scroll position."""
        self._pivot_rows = rows
        self.table_pivot.setRowCount(len(rows))

        for row, c in enumerate(rows):
            self.table_pivot.setItem(row, 0, QTableWidgetItem(c["name"]))
            self._set_right_item(self.table_pivot, row, 1, str(c["invoices"]))
            self._set_right_item(self.table_pivot, row, 2, f"{cfg.CURRENCY_SYMBOL} {c['discount']:,.2f}")
            self._set_right_item(self.table_pivot, row, 3, f"{cfg.CURRENCY_SYMBOL} {c['grand_total']:,.2f}")
            self._set_right_item(self.table_pivot, row, 4, f"{cfg.CURRENCY_SYMBOL} {c['paid']:,.2f}")
            due_item = QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {c['due']:,.2f}")
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if c["due"] > 0:
                due_item.setForeground(QColor(cfg.resolve_status_color("due")))
            self.table_pivot.setItem(row, 5, due_item)
            self.table_pivot.setItem(row, 6, QTableWidgetItem(c["last_purchase"] or "—"))
            self._set_right_item(self.table_pivot, row, 7, f"{c['compost_kg']:,.2f}")
            self._set_right_item(self.table_pivot, row, 8, f"{c['worms_kg']:,.2f}")

            btn_ledger = QPushButton("🧾")
            btn_ledger.setToolTip("View Invoice Ledger")
            btn_ledger.setStyleSheet(_LEDGER_BTN)
            btn_ledger.clicked.connect(lambda checked, cid=c["id"], cname=c["name"]: self.view_ledger_requested.emit(cid, cname))
            wrap = QWidget()
            wrap_layout = QHBoxLayout(wrap)
            wrap_layout.setContentsMargins(2, 2, 2, 2)
            wrap_layout.addWidget(btn_ledger)
            self.table_pivot.setCellWidget(row, 9, wrap)

        # --- Frozen TOTAL footer row (separate table -- always visible) ---
        bold_font = QFont()
        bold_font.setBold(True)

        def _total_item(text, align_right=True):
            item = QTableWidgetItem(text)
            item.setFont(bold_font)
            if align_right:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return item

        self.table_pivot_totals.setItem(0, 0, _total_item(f"TOTAL ({len(rows)} customers)", align_right=False))
        self.table_pivot_totals.setItem(0, 1, _total_item(str(totals["invoices"])))
        self.table_pivot_totals.setItem(0, 2, _total_item(f"{cfg.CURRENCY_SYMBOL} {totals['discount']:,.2f}"))
        self.table_pivot_totals.setItem(0, 3, _total_item(f"{cfg.CURRENCY_SYMBOL} {totals['grand_total']:,.2f}"))
        self.table_pivot_totals.setItem(0, 4, _total_item(f"{cfg.CURRENCY_SYMBOL} {totals['paid']:,.2f}"))
        self.table_pivot_totals.setItem(0, 5, _total_item(f"{cfg.CURRENCY_SYMBOL} {totals['due']:,.2f}"))
        self.table_pivot_totals.setItem(0, 6, _total_item("—", align_right=False))  # not summable
        self.table_pivot_totals.setItem(0, 7, _total_item(f"{totals['compost_kg']:,.2f}"))
        self.table_pivot_totals.setItem(0, 8, _total_item(f"{totals['worms_kg']:,.2f}"))
        self.table_pivot_totals.setItem(0, 9, _total_item(""))

        self._apply_search_filter(self.search_input.text())

    def _set_right_item(self, table: QTableWidget, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        table.setItem(row, col, item)

    # ---------------- Search (client-side row visibility) ----------------
    def _apply_search_filter(self, text: str):
        needle = (text or "").strip().lower()

        for row, c in enumerate(self._directory_rows):
            haystack = f"{c['name']} {c['phone']}".lower()
            self.table_directory.setRowHidden(row, bool(needle) and needle not in haystack)

        # Pivot: only iterate actual customer rows -- the TOTAL row (last index)
        # is always kept visible regardless of the search term.
        for row, c in enumerate(self._pivot_rows):
            haystack = c["name"].lower()
            self.table_pivot.setRowHidden(row, bool(needle) and needle not in haystack)