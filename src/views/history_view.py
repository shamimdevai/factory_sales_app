from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFrame, QMessageBox, QFileDialog,
    QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QColor
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
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        # Title
        title = QLabel("Sales History Ledger")
        title.setFont(QFont("Segue UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        self.main_layout.addWidget(title)

        self._init_filter_bar()
        self._init_history_table()

    def _init_filter_bar(self):
        filter_frame = QFrame()
        filter_frame.setStyleSheet(theme.card_frame_style())
        layout = QHBoxLayout(filter_frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        input_style = theme.input_style("QDateEdit, QLineEdit, QComboBox")

        # "Filter By" mode selector
        layout.addWidget(QLabel("Filter By:"))
        self.filter_by_combo = QComboBox()
        self.filter_by_combo.addItems(["Date Range", "Invoice ID", "Customer Name", "Status"])
        self.filter_by_combo.setStyleSheet(input_style)
        self.filter_by_combo.currentTextChanged.connect(self._on_filter_mode_changed)
        layout.addWidget(self.filter_by_combo)

        # --- Date Range inputs (default mode) ---
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
        layout.addWidget(self.date_range_widget)

        # --- Invoice ID input ---
        self.invoice_id_input = QLineEdit()
        self.invoice_id_input.setPlaceholderText("Enter Invoice ID (e.g. 25)")
        self.invoice_id_input.setStyleSheet(input_style)
        self.invoice_id_input.setVisible(False)
        layout.addWidget(self.invoice_id_input)

        # --- Customer Name input ---
        self.customer_name_input = QLineEdit()
        self.customer_name_input.setPlaceholderText("Enter Customer Name")
        self.customer_name_input.setStyleSheet(input_style)
        self.customer_name_input.setVisible(False)
        layout.addWidget(self.customer_name_input)

        # --- Status dropdown ---
        self.status_combo = QComboBox()
        self.status_combo.addItems(self.STATUS_OPTIONS)
        self.status_combo.setStyleSheet(input_style)
        self.status_combo.setVisible(False)
        layout.addWidget(self.status_combo)

        # Search button (renamed from "Filter")
        btn_search = QPushButton("🔍 Search")
        btn_search.setStyleSheet(
            "QPushButton { background-color: #34495e; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2c3e50; }")
        btn_search.clicked.connect(self._on_search_clicked)
        layout.addWidget(btn_search)

        # Export Buttons
        self.btn_export_excel = QPushButton("🟢 Export to Excel")
        self.btn_export_excel.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #219653; }")
        self.btn_export_excel.clicked.connect(self._on_export_excel_clicked)

        self.btn_export_pdf = QPushButton("🔴 Export Summary PDF")
        self.btn_export_pdf.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #a33226; }")
        self.btn_export_pdf.clicked.connect(self._on_export_pdf_clicked)

        layout.addStretch()
        layout.addWidget(self.btn_export_excel)
        layout.addWidget(self.btn_export_pdf)

        self.main_layout.addWidget(filter_frame)

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

        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(f"QTableWidget {{ background: {theme.CARD_BACKGROUND}; border: 1px solid {theme.BORDER_COLOR}; }}")
        self.main_layout.addWidget(self.table)

    def _on_filter_mode_changed(self, mode: str):
        """Show only the input widget(s) relevant to the selected filter mode."""
        self.date_range_widget.setVisible(mode == "Date Range")
        self.invoice_id_input.setVisible(mode == "Invoice ID")
        self.customer_name_input.setVisible(mode == "Customer Name")
        self.status_combo.setVisible(mode == "Status")

    def get_current_filter(self) -> dict:
        """Builds the filter dict for whichever mode is currently selected."""
        mode = self.filter_by_combo.currentText()
        if mode == "Date Range":
            return {"mode": "date", "start": self.date_start.date(), "end": self.date_end.date()}
        elif mode == "Invoice ID":
            return {"mode": "invoice_id", "value": self.invoice_id_input.text().strip()}
        elif mode == "Customer Name":
            return {"mode": "customer_name", "value": self.customer_name_input.text().strip()}
        elif mode == "Status":
            return {"mode": "status", "value": self.status_combo.currentText()}
        return {"mode": "date", "start": self.date_start.date(), "end": self.date_end.date()}

    def _on_search_clicked(self):
        filter_dict = self.get_current_filter()
        if filter_dict["mode"] in ("invoice_id", "customer_name") and not filter_dict.get("value"):
            label = "Invoice ID" if filter_dict["mode"] == "invoice_id" else "Customer Name"
            QMessageBox.warning(self, "Missing Input", f"Please enter a value to search by {label}.")
            return
        self.search_requested.emit(filter_dict)

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