from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFrame, QMessageBox, QFileDialog,
    QComboBox, QLineEdit, QToolButton, QMenu
)
from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction
from src.config import company_config as cfg
from src.config import theme

class HistoryView(QWidget):
    search_requested = pyqtSignal(dict)          # {"mode": ..., ...params}
    export_excel_requested = pyqtSignal(dict, str)
    export_pdf_requested = pyqtSignal(dict, str)
    reprint_invoice_requested = pyqtSignal(int, str)
    pay_due_requested = pyqtSignal(int)             # root invoice id
    view_payment_history_requested = pyqtSignal(int)  # root invoice id

    STATUS_OPTIONS = ["Paid", "Due", "Partial Payment"]

    def __init__(self):
        super().__init__()
        self._customer_filter_active = None  # set via apply_customer_filter(); overrides everything below
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        # Title
        title = QLabel("Sales History Ledger")
        title.setFont(QFont("Segue UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        self.main_layout.addWidget(title)

        self._init_customer_filter_banner()
        self._init_filter_bar()
        self._init_history_table()

    def _init_customer_filter_banner(self):
        """Hidden by default. Shown only when navigated here via a Customer's
        'View Ledger' action (see apply_customer_filter)."""
        self.customer_filter_banner = QFrame()
        self.customer_filter_banner.setStyleSheet(
            f"QFrame {{ background: {theme.PAGE_BACKGROUND}; border: 1px solid {theme.ACCENT}; border-radius: 6px; }}")
        self.customer_filter_banner.setVisible(False)
        banner_layout = QHBoxLayout(self.customer_filter_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_customer_filter = QLabel("")
        self.lbl_customer_filter.setStyleSheet(f"border: none; font-weight: bold; color: {theme.ACCENT_DARK};")
        banner_layout.addWidget(self.lbl_customer_filter)
        banner_layout.addStretch()

        btn_clear = QPushButton("✖ Clear Filter")
        btn_clear.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; padding: 4px 12px; border-radius: 4px; } QPushButton:hover { background-color: #7f8c8d; }")
        btn_clear.clicked.connect(self._on_clear_customer_filter)
        banner_layout.addWidget(btn_clear)

        self.main_layout.addWidget(self.customer_filter_banner)

    def _init_filter_bar(self):
        filter_frame = QFrame()
        filter_frame.setStyleSheet(theme.card_frame_style())
        layout = QHBoxLayout(filter_frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        input_style = theme.input_style("QDateEdit, QLineEdit, QComboBox")

        # "Filter By" mode selector -- "Quick Search" is the default/first mode
        layout.addWidget(QLabel("Filter By:"))
        self.filter_by_combo = QComboBox()
        self.filter_by_combo.addItems(["Quick Search", "Date Range", "Status"])
        self.filter_by_combo.setStyleSheet(input_style)
        self.filter_by_combo.currentTextChanged.connect(self._on_filter_mode_changed)
        layout.addWidget(self.filter_by_combo)

        # --- Quick Search (default mode): one box, live/auto, searches everything ---
        self.quick_search_input = QLineEdit()
        self.quick_search_input.setPlaceholderText(
            "Search by Invoice ID, Name, Phone, Date, Status, or Amount...")
        self.quick_search_input.setStyleSheet(input_style)
        self.quick_search_input.textChanged.connect(self._on_quick_search_text_changed)
        layout.addWidget(self.quick_search_input, 1)

        # Debounce: wait for a short pause in typing before actually querying,
        # so we don't hit the DB on every single keystroke.
        self._quick_search_timer = QTimer(self)
        self._quick_search_timer.setSingleShot(True)
        self._quick_search_timer.setInterval(300)
        self._quick_search_timer.timeout.connect(self._emit_quick_search)

        # --- Date Range inputs ---
        self.date_range_widget = QWidget()
        date_range_layout = QHBoxLayout(self.date_range_widget)
        date_range_layout.setContentsMargins(0, 0, 0, 0)
        date_range_layout.setSpacing(10)
        self.date_start = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_start.setCalendarPopup(True)
        self.date_start.setStyleSheet(input_style)
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setStyleSheet(input_style)
        date_range_layout.addWidget(QLabel("Start Date:"))
        date_range_layout.addWidget(self.date_start)
        date_range_layout.addWidget(QLabel("End Date:"))
        date_range_layout.addWidget(self.date_end)
        self.date_range_widget.setVisible(False)
        layout.addWidget(self.date_range_widget)

        # --- Status dropdown ---
        self.status_combo = QComboBox()
        self.status_combo.addItems(self.STATUS_OPTIONS)
        self.status_combo.setStyleSheet(input_style)
        self.status_combo.setVisible(False)
        layout.addWidget(self.status_combo)

        # Search button -- only needed for Date Range / Status (explicit-action modes)
        self.btn_search = QPushButton("🔍 Search")
        self.btn_search.setStyleSheet(
            "QPushButton { background-color: #34495e; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2c3e50; }")
        self.btn_search.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.btn_search)

        # Clear Search -- always available, resets everything back to
        # "Quick Search" mode with an empty box (i.e. show all records).
        btn_clear_search = QPushButton("✖ Clear Search")
        btn_clear_search.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #7f8c8d; }")
        btn_clear_search.clicked.connect(self._on_clear_search_clicked)
        layout.addWidget(btn_clear_search)

        # Single "Export" button with a dropdown menu -- click to reveal PDF/Excel,
        # easy to add more formats later without adding more buttons to this row.
        self.btn_export = QToolButton()
        self.btn_export.setText("⬇ Export")
        self.btn_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_export.setStyleSheet(
            "QToolButton { background-color: #16a085; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } "
            "QToolButton:hover { background-color: #138a72; }")

        export_menu = QMenu(self.btn_export)
        export_menu.setStyleSheet(
            f"QMenu {{ background-color: {theme.CARD_BACKGROUND}; border: 1px solid {theme.BORDER_COLOR}; padding: 4px; }} "
            f"QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 3px; }} "
            f"QMenu::item:selected {{ background-color: {theme.ACCENT}; color: white; }}")

        self.action_export_pdf = QAction("🔴 Export to PDF", self)
        self.action_export_pdf.triggered.connect(self._on_export_pdf_clicked)
        export_menu.addAction(self.action_export_pdf)

        self.action_export_excel = QAction("🟢 Export to Excel", self)
        self.action_export_excel.triggered.connect(self._on_export_excel_clicked)
        export_menu.addAction(self.action_export_excel)

        self.btn_export.setMenu(export_menu)

        layout.addStretch()
        layout.addWidget(self.btn_export)

        self.main_layout.addWidget(filter_frame)

        # Apply correct initial widget visibility for the default mode -- this
        # method is otherwise only triggered by the combo's currentTextChanged
        # signal, which does NOT fire just from building the widgets above, so
        # without this the Search button incorrectly stays visible on first
        # load until the operator manually changes mode or clicks Clear Search.
        self._on_filter_mode_changed(self.filter_by_combo.currentText())

    def _init_history_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Invoice ID", "Customer Name", "Date", "Discount", "Grand Total","Status", "Due", "Actions"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        # Actions column widened (150) to fit up to 3 stacked action buttons
        column_widths = [80, 160, 130, 100, 110, 110, 100, 150]
        for col, width in enumerate(column_widths):
            self.table.setColumnWidth(col, width)

        self.table.verticalHeader().setVisible(False)  # no default row-number column
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(f"QTableWidget {{ background: {theme.CARD_BACKGROUND}; border: 1px solid {theme.BORDER_COLOR}; }}")
        self.main_layout.addWidget(self.table)

    def _on_filter_mode_changed(self, mode: str):
        """Show only the input widget(s) relevant to the selected filter mode."""
        self.quick_search_input.setVisible(mode == "Quick Search")
        self.date_range_widget.setVisible(mode == "Date Range")
        self.status_combo.setVisible(mode == "Status")
        self.btn_search.setVisible(mode != "Quick Search")  # Quick Search is live, no button needed

        # Manually picking a filter mode means the operator wants a fresh
        # search -- drop any customer-ledger override from apply_customer_filter().
        if self._customer_filter_active is not None:
            self._customer_filter_active = None
            self.customer_filter_banner.setVisible(False)

        if mode == "Quick Search":
            self._emit_quick_search()  # show current/empty quick-search results immediately

    def get_current_filter(self) -> dict:
        """Builds the filter dict for whichever mode is currently selected. An
        active customer-ledger override (see apply_customer_filter) takes
        priority over the Filter By dropdown until explicitly cleared."""
        if self._customer_filter_active is not None:
            return self._customer_filter_active
        mode = self.filter_by_combo.currentText()
        if mode == "Quick Search":
            return {"mode": "quick_search", "value": self.quick_search_input.text().strip()}
        elif mode == "Date Range":
            return {"mode": "date", "start": self.date_start.date(), "end": self.date_end.date()}
        elif mode == "Status":
            return {"mode": "status", "value": self.status_combo.currentText()}
        return {"mode": "quick_search", "value": ""}

    def _on_search_clicked(self):
        self.search_requested.emit(self.get_current_filter())

    def _on_quick_search_text_changed(self, text: str):
        self._quick_search_timer.start()  # restarts on every keystroke; fires 300ms after typing pauses

    def _emit_quick_search(self):
        self.search_requested.emit(self.get_current_filter())

    def _on_clear_search_clicked(self):
        self._customer_filter_active = None
        self.customer_filter_banner.setVisible(False)

        self.quick_search_input.blockSignals(True)
        self.quick_search_input.clear()
        self.quick_search_input.blockSignals(False)

        self.filter_by_combo.blockSignals(True)
        self.filter_by_combo.setCurrentIndex(0)  # "Quick Search"
        self.filter_by_combo.blockSignals(False)
        self._on_filter_mode_changed("Quick Search")  # signals were blocked above -- apply visibility manually

        self.search_requested.emit({"mode": "quick_search", "value": ""})  # empty value -> show all

    def apply_customer_filter(self, customer_id: int, customer_name: str):
        """Called by main_window.py when navigating here from a Customer's
        'View Ledger' action. Overrides everything else with an exact
        customer_id match until cleared or a manual filter mode is chosen."""
        self._customer_filter_active = {"mode": "customer_id", "customer_id": customer_id}
        self.lbl_customer_filter.setText(f"Showing ledger for: {customer_name} (Customer #{customer_id})")
        self.customer_filter_banner.setVisible(True)
        self.search_requested.emit(self._customer_filter_active)

    def _on_clear_customer_filter(self):
        self._customer_filter_active = None
        self.customer_filter_banner.setVisible(False)
        self.search_requested.emit(self.get_current_filter())  # re-run using whatever the filter bar is currently set to

    def _on_export_excel_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Excel Ledger", "", "Excel Files (*.xlsx)")
        if file_path:
            self.export_excel_requested.emit(self.get_current_filter(), file_path)

    def _on_export_pdf_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Summary PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.export_pdf_requested.emit(self.get_current_filter(), file_path)

    def populate_table(self, records: list):
        self.table.setRowCount(0)
        for idx, row in enumerate(records):
            self.table.insertRow(idx)
            self.table.setItem(idx, 0, QTableWidgetItem(f"#{row['id']}"))
            self.table.setItem(idx, 1, QTableWidgetItem(row['customer_name']))
            self.table.setItem(idx, 2, QTableWidgetItem(row['date']))

            discount_item = QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {row['discount']:,.2f}")
            discount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(idx, 3, discount_item)

            total_item = QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {row['grand_total']:,.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(idx, 4, total_item)

            # NOTE: 'status' / 'due' are the EFFECTIVE (dynamically computed) values —
            # they reflect any linked due-payments, not just the invoice's own stored fields.
            status_item = QTableWidgetItem(row['status'])
            status_item.setForeground(QColor(cfg.resolve_status_color(row['status'])))
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(idx, 5, status_item)

            due_item = QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {row['due']:,.2f}")
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if row['due'] > 0:
                due_item.setForeground(QColor(cfg.resolve_status_color(row['status'])))
            self.table.setItem(idx, 6, due_item)

            # Actions cell: PDF (always) + Pay Due (if due > 0) + History (if any due-payments exist)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            btn_reprint = QPushButton("📄")
            btn_reprint.setToolTip("Download PDF")
            btn_reprint.setStyleSheet(
                "QPushButton { background-color: #3498db; color: white; font-size: 11px; max-width: 28px; border-radius: 3px; } QPushButton:hover { background-color: #2980b9; }")
            btn_reprint.clicked.connect(lambda checked, i_id=row['id']: self._trigger_reprint(i_id))
            actions_layout.addWidget(btn_reprint)

            if row['due'] > 0:
                btn_pay_due = QPushButton("💰")
                btn_pay_due.setToolTip("Record Due Payment")
                btn_pay_due.setStyleSheet(
                    "QPushButton { background-color: #27ae60; color: white; font-size: 11px; max-width: 28px; border-radius: 3px; } QPushButton:hover { background-color: #219653; }")
                btn_pay_due.clicked.connect(lambda checked, i_id=row['id']: self.pay_due_requested.emit(i_id))
                actions_layout.addWidget(btn_pay_due)

            if row.get('has_due_payments'):
                btn_history = QPushButton("🧾")
                btn_history.setToolTip("View Payment History")
                btn_history.setStyleSheet(
                    "QPushButton { background-color: #8e44ad; color: white; font-size: 11px; max-width: 28px; border-radius: 3px; } QPushButton:hover { background-color: #6c3483; }")
                btn_history.clicked.connect(lambda checked, i_id=row['id']: self.view_payment_history_requested.emit(i_id))
                actions_layout.addWidget(btn_history)

            actions_layout.addStretch()
            self.table.setCellWidget(idx, 7, actions_widget)

    def _trigger_reprint(self, invoice_id: int):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Invoice PDF", f"Invoice_{invoice_id}.pdf",
                                                   "PDF Files (*.pdf)")
        if file_path:
            self.reprint_invoice_requested.emit(invoice_id, file_path)