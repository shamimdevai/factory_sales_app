from datetime import date
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem, \
    QHeaderView, QComboBox, QSpinBox, QDateEdit, QPushButton
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from src.config import company_config as cfg
from src.config import theme

class DashboardView(QWidget):
    view_period_requested = pyqtSignal(dict)  # {"mode": "today"/"all"/"month"/"year"/"range", ...params}

    MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # Header title
        self.title = QLabel("Dashboard Analytics")
        self.title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.title.setStyleSheet("color: #2c3e50;")
        self.main_layout.addWidget(self.title)

        self._init_period_selector()
        self._init_kpi_cards()
        self._init_recent_sales_table()

    def _init_period_selector(self):
        """Row 1 — period/view selector (Today / All / Month / Year / Date Range) that
        drives what the 4 KPI cards below summarize. Visually distinct (light blue tint)
        from the KPI card row beneath it."""
        period_frame = QFrame()
        period_frame.setStyleSheet("""
            QFrame { background-color: rgba(52, 152, 219, 0.10); border-radius: 8px; }
        """)
        layout = QHBoxLayout(period_frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(12)

        input_style = theme.input_style("QComboBox, QSpinBox, QDateEdit")

        layout.addWidget(QLabel("View:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Today", "Month", "Year", "Date Range", "All"])
        self.view_mode_combo.setStyleSheet(input_style)
        self.view_mode_combo.currentTextChanged.connect(self._on_view_mode_changed)
        layout.addWidget(self.view_mode_combo)

        current_year = date.today().year

        # --- Month mode: month name + year ---
        self.month_combo = QComboBox()
        self.month_combo.addItems(self.MONTH_NAMES)
        self.month_combo.setCurrentIndex(date.today().month - 1)
        self.month_combo.setStyleSheet(input_style)
        self.month_combo.setVisible(False)
        layout.addWidget(self.month_combo)

        # --- Year spinner: shared by Month mode and Year mode ---
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(current_year)
        self.year_spin.setStyleSheet(input_style)
        self.year_spin.setVisible(False)
        layout.addWidget(self.year_spin)

        # --- Date Range mode: start/end date pickers ---
        self.range_widget = QWidget()
        range_layout = QHBoxLayout(self.range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(10)
        self.range_start = QDateEdit(QDate.currentDate().addDays(-7))
        self.range_start.setCalendarPopup(True)
        self.range_start.setStyleSheet(input_style)
        self.range_end = QDateEdit(QDate.currentDate())
        self.range_end.setCalendarPopup(True)
        self.range_end.setStyleSheet(input_style)
        range_layout.addWidget(QLabel("From:"))
        range_layout.addWidget(self.range_start)
        range_layout.addWidget(QLabel("To:"))
        range_layout.addWidget(self.range_end)
        self.range_widget.setVisible(False)
        layout.addWidget(self.range_widget)

        btn_view = QPushButton("🔍 View")
        btn_view.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #21618c; }")
        btn_view.clicked.connect(self._on_view_clicked)
        layout.addWidget(btn_view)

        layout.addStretch()
        self.main_layout.addWidget(period_frame)

    def _on_view_mode_changed(self, mode: str):
        self.month_combo.setVisible(mode == "Month")
        self.year_spin.setVisible(mode in ("Month", "Year"))
        self.range_widget.setVisible(mode == "Date Range")

    def get_current_period(self) -> dict:
        """Builds the period filter dict for whichever view mode is currently selected."""
        mode = self.view_mode_combo.currentText()
        if mode == "Today":
            return {"mode": "today"}
        elif mode == "All":
            return {"mode": "all"}
        elif mode == "Month":
            return {"mode": "month", "month": self.month_combo.currentIndex() + 1, "year": self.year_spin.value()}
        elif mode == "Year":
            return {"mode": "year", "year": self.year_spin.value()}
        elif mode == "Date Range":
            return {"mode": "range", "start": self.range_start.date(), "end": self.range_end.date()}
        return {"mode": "today"}

    def _on_view_clicked(self):
        self.view_period_requested.emit(self.get_current_period())

    def _init_kpi_cards(self):
        """Row 2 — the 4 KPI cards, wrapped in a frame with a different transparent tint
        so it's visually distinct from the period-selector row above."""
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("""
            QFrame { background-color: rgba(149, 165, 166, 0.08); border-radius: 8px; }
        """)
        kpi_outer_layout = QVBoxLayout(kpi_frame)
        kpi_outer_layout.setContentsMargins(15, 15, 15, 15)

        self.period_label = QLabel("Showing: Today")
        self.period_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.period_label.setStyleSheet("color: #7f8c8d;")
        kpi_outer_layout.addWidget(self.period_label)

        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(20)

        self.card_revenue = self._create_card("Total Revenue", f"{cfg.CURRENCY_SYMBOL} 0.00", "#2ecc71")
        self.card_compost = self._create_card("Compost Sold", "0.00 kg", "#3498db")
        self.card_worms = self._create_card("Worms Sold", "0.00 kg", "#9b59b6")
        self.card_invoices = self._create_card("Total Invoices", "0", "#f1c40f")

        kpi_layout.addWidget(self.card_revenue)
        kpi_layout.addWidget(self.card_compost)
        kpi_layout.addWidget(self.card_worms)
        kpi_layout.addWidget(self.card_invoices)

        kpi_outer_layout.addLayout(kpi_layout)
        self.main_layout.addWidget(kpi_frame)

    def _create_card(self, title: str, val: str, color: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.CARD_BACKGROUND};
                border-radius: 8px;
                border-left: 5px solid {color};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        title_lbl.setStyleSheet("color: #7f8c8d;")

        value_lbl = QLabel(val)
        value_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        value_lbl.setStyleSheet("color: #2c3e50;")

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)

        card.value_label = value_lbl
        return card

    def _init_recent_sales_table(self):
        table_container = QVBoxLayout()
        table_container.setSpacing(10)

        lbl = QLabel("Recent 10 Records")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #2c3e50;")
        table_container.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Invoice ID", "Customer Name", "Date", "Items Count", "Grand Total", "Status", "Due", "Payment"])

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        resize_modes = {
            0: QHeaderView.ResizeMode.ResizeToContents,
            1: QHeaderView.ResizeMode.Interactive,
            2: QHeaderView.ResizeMode.ResizeToContents,
            3: QHeaderView.ResizeMode.ResizeToContents,
            4: QHeaderView.ResizeMode.ResizeToContents,
            5: QHeaderView.ResizeMode.Interactive,
            6: QHeaderView.ResizeMode.ResizeToContents,
            7: QHeaderView.ResizeMode.ResizeToContents,
        }
        for col, mode in resize_modes.items():
            header.setSectionResizeMode(col, mode)

        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(5, 130)

        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)

        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.CARD_BACKGROUND};
                gridline-color: {theme.BORDER_COLOR};
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background-color: #f1f5f9;
                color: #475569;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid {theme.BORDER_COLOR};
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
        """)

        table_container.addWidget(self.table)
        self.main_layout.addLayout(table_container)

    def update_metrics(self, revenue: float, compost: float, worms: float, invoices: int, period_label: str):
        """Update KPI numerical displays dynamically, plus the small 'Showing: ...' caption."""
        self.period_label.setText(f"Showing: {period_label}")
        self.card_revenue.value_label.setText(f"{cfg.CURRENCY_SYMBOL} {revenue:,.2f}")
        self.card_compost.value_label.setText(f"{compost:,.2f} kg")
        self.card_worms.value_label.setText(f"{worms:,.2f} kg")
        self.card_invoices.value_label.setText(str(invoices))

    def populate_recent_sales(self, records: list):
        """Populate the table widget with recent transactions AND due-payment records."""
        self.table.setRowCount(0)
        default_text_color = QColor("#334155")

        for row_idx, rec in enumerate(records):
            self.table.insertRow(row_idx)
            is_due_payment = rec.get('is_due_payment', False)

            id_item = QTableWidgetItem(f"#{rec['id']}")
            id_item.setForeground(QColor("#8e44ad") if is_due_payment else default_text_color)
            self.table.setItem(row_idx, 0, id_item)

            name_item = QTableWidgetItem(rec['customer_name'])
            name_item.setForeground(default_text_color)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, name_item)

            date_item = QTableWidgetItem(rec['date'])
            date_item.setForeground(default_text_color)
            self.table.setItem(row_idx, 2, date_item)

            items_item = QTableWidgetItem(str(rec['items_count']))
            items_item.setForeground(default_text_color)
            items_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, items_item)

            grand_total_text = "—" if rec['grand_total'] is None else f"{cfg.CURRENCY_SYMBOL} {rec['grand_total']:,.2f}"
            grand_total_item = QTableWidgetItem(grand_total_text)
            grand_total_item.setForeground(default_text_color)
            grand_total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 4, grand_total_item)

            status_item = QTableWidgetItem(rec['status'])
            status_color = "#8e44ad" if is_due_payment else cfg.resolve_status_color(rec['status'])
            status_item.setForeground(QColor(status_color))
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 5, status_item)

            due_text = "—" if rec['due'] is None else f"{cfg.CURRENCY_SYMBOL} {rec['due']:,.2f}"
            due_item = QTableWidgetItem(due_text)
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if rec['due'] and rec['due'] > 0:
                due_item.setForeground(QColor(cfg.resolve_status_color(rec['status'])))
            else:
                due_item.setForeground(default_text_color)
            self.table.setItem(row_idx, 6, due_item)

            payment_item = QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {rec['payment']:,.2f}")
            payment_item.setForeground(default_text_color)
            payment_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 7, payment_item)

        self.table.resizeRowsToContents()