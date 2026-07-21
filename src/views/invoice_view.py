from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from src.config import company_config as cfg
from src.config import theme


class InvoiceView(QWidget):
    # Custom signals for controller interaction
    add_item_requested = pyqtSignal(str, float, float)  # Name, Quantity, Unit Price
    remove_item_requested = pyqtSignal(int)              # Row Index
    billing_changed = pyqtSignal()                       # Discount/VAT/Adjustment edited — recompute totals
    submit_invoice_requested = pyqtSignal(dict)           # Full invoice payload
    generate_pdf_requested = pyqtSignal(int)              # Invoice ID

    def __init__(self):
        super().__init__()
        self.last_invoice_id = None
        self.current_grand_total = 0.0

        # Minimum natural width for this screen's content. Below this, the
        # QScrollArea that main_window.py wraps every page in will show a
        # horizontal scrollbar rather than squeezing the layout unreadable.
        self.setMinimumWidth(900)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        title = QLabel("Interactive Invoice Terminal")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        self.main_layout.addWidget(title)

        workspace = QHBoxLayout()
        workspace.setSpacing(20)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)
        left_panel.addWidget(self._create_customer_box())
        left_panel.addWidget(self._create_item_input_box())
        workspace.addLayout(left_panel, 2)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        right_panel.addWidget(self._create_items_grid())
        right_panel.addWidget(self._create_metrics_box())
        workspace.addLayout(right_panel, 3)

        self.main_layout.addLayout(workspace)

    def _create_customer_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl = QLabel("1. Customer Details")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        layout.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)

        self.txt_cust_name = QLineEdit()
        self.txt_cust_phone = QLineEdit()
        self.txt_cust_email = QLineEdit()
        self.txt_cust_address = QLineEdit()

        input_style = theme.input_style("QLineEdit")
        for f in [self.txt_cust_name, self.txt_cust_phone, self.txt_cust_email, self.txt_cust_address]:
            f.setStyleSheet(input_style)

        form.addRow("Name *:", self.txt_cust_name)
        form.addRow("Phone *:", self.txt_cust_phone)
        form.addRow("Email:", self.txt_cust_email)
        form.addRow("Address:", self.txt_cust_address)

        layout.addLayout(form)
        return frame

    def _create_item_input_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl = QLabel("2. Add Products")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        layout.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(8)

        self.combo_product = QComboBox()
        self.combo_product.addItems(["Premium Vermi-Compost", "Organic Earthworm Castings", "Compost Starter Culture", "Liquid Bio-Fertilizer"])
        self.combo_product.setStyleSheet(f"""
            {theme.input_style("QComboBox")}
            {theme.combobox_dropdown_style()}
        """)

        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.1, 10000.0)
        self.spin_qty.setValue(10.0)
        self.spin_qty.setSuffix(" kg")

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(1.0, 100000.0)
        self.spin_price.setValue(25.0)
        self.spin_price.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")

        spin_style = theme.input_style("QDoubleSpinBox")
        self.spin_qty.setStyleSheet(spin_style)
        self.spin_price.setStyleSheet(spin_style)

        form.addRow("Select Product:", self.combo_product)
        form.addRow("Quantity:", self.spin_qty)
        form.addRow("Unit Price:", self.spin_price)

        layout.addLayout(form)
        layout.addSpacing(10)

        btn_add = QPushButton("➕ Add to Invoice")
        btn_add.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2980b9; }")
        btn_add.clicked.connect(self._on_add_clicked)
        layout.addWidget(btn_add)

        return frame

    def _create_items_grid(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl = QLabel("3. Cart Items")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Product Description", "Qty", "Price", "Subtotal"])

        # Fixed column widths + native scrollbars instead of force-stretch, so
        # this table behaves consistently with the other tables in the app.
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        for col, width in enumerate([220, 90, 110, 110]):
            self.table.setColumnWidth(col, width)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.table.setStyleSheet(f"QTableWidget {{ background: {theme.CARD_BACKGROUND}; border: 1px solid {theme.BORDER_COLOR}; }}")
        layout.addWidget(self.table)

        btn_remove = QPushButton("❌ Remove Selected Row")
        btn_remove.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; padding: 6px; border-radius: 4px; font-size: 11px; } QPushButton:hover { background-color: #c0392b; }")
        btn_remove.clicked.connect(self._on_remove_clicked)
        layout.addWidget(btn_remove)

        return frame

    def _create_metrics_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        spin_style = theme.input_style("QDoubleSpinBox")

        # --- Billing adjustments grid: Discount / VAT / Less Adjustment ---
        # QGridLayout (not QHBoxLayout) so it always wraps onto a fixed number
        # of rows instead of extending sideways indefinitely on narrow windows.
        billing_grid = QGridLayout()
        billing_grid.setHorizontalSpacing(10)
        billing_grid.setVerticalSpacing(8)

        self.spin_discount = QDoubleSpinBox()
        self.spin_discount.setRange(0.0, 10_000_000.0)
        self.spin_discount.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")
        self.spin_discount.setValue(0.0)
        self.spin_discount.setStyleSheet(spin_style)
        self.spin_discount.valueChanged.connect(lambda _: self.billing_changed.emit())

        self.spin_tax_percent = QDoubleSpinBox()
        self.spin_tax_percent.setRange(0.0, 100.0)
        self.spin_tax_percent.setSuffix(" %")
        self.spin_tax_percent.setValue(0.0)  # Default 0%
        self.spin_tax_percent.setStyleSheet(spin_style)
        self.spin_tax_percent.valueChanged.connect(lambda _: self.billing_changed.emit())

        self.spin_adjustment = QDoubleSpinBox()
        self.spin_adjustment.setRange(0.0, 10_000_000.0)
        self.spin_adjustment.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")
        self.spin_adjustment.setValue(0.0)
        self.spin_adjustment.setStyleSheet(spin_style)
        self.spin_adjustment.valueChanged.connect(lambda _: self.billing_changed.emit())

        billing_grid.addWidget(QLabel("Discount:"), 0, 0)
        billing_grid.addWidget(self.spin_discount, 0, 1)
        billing_grid.addWidget(QLabel("VAT:"), 0, 2)
        billing_grid.addWidget(self.spin_tax_percent, 0, 3)
        billing_grid.addWidget(QLabel("Less Adj:"), 1, 0)
        billing_grid.addWidget(self.spin_adjustment, 1, 1)
        billing_grid.setColumnStretch(4, 1)

        layout.addLayout(billing_grid)
        layout.addSpacing(4)

        # --- Totals grid: fixed 3 columns x 2 rows, always wraps ---
        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(15)
        metrics_grid.setVerticalSpacing(6)

        self.lbl_subtotal = QLabel(f"Subtotal: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_discount_display = QLabel(f"Discount: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_tax = QLabel(f"VAT: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_adjustment_display = QLabel(f"Less Adj: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_total = QLabel(f"Grand Total: {cfg.CURRENCY_SYMBOL} 0.00")

        metric_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        for label in [self.lbl_subtotal, self.lbl_discount_display, self.lbl_tax, self.lbl_adjustment_display, self.lbl_total]:
            label.setFont(metric_font)
            label.setStyleSheet("color: #2c3e50;")

        metrics_grid.addWidget(self.lbl_subtotal, 0, 0)
        metrics_grid.addWidget(self.lbl_discount_display, 0, 1)
        metrics_grid.addWidget(self.lbl_tax, 0, 2)
        metrics_grid.addWidget(self.lbl_adjustment_display, 1, 0)
        metrics_grid.addWidget(self.lbl_total, 1, 1)

        layout.addLayout(metrics_grid)
        layout.addSpacing(4)

        # --- Payment info row (its own grid, buttons on a separate row below) ---
        payment_grid = QGridLayout()
        payment_grid.setHorizontalSpacing(10)
        payment_grid.setVerticalSpacing(8)

        self.combo_payment = QComboBox()
        self.combo_payment.addItems(["Paid", "Due", "Partial Payment"])
        self.combo_payment.setStyleSheet(f"""
            QComboBox {{ padding: 6px; border: 1px solid {theme.BORDER_COLOR}; border-radius: 4px; background: {theme.CARD_BACKGROUND}; color: {theme.TEXT_PRIMARY}; }}
            {theme.combobox_dropdown_style()}
        """)
        self.combo_payment.currentTextChanged.connect(self._on_payment_status_changed)

        self.lbl_payment_field = QLabel("Payment:")
        self.lbl_payment_field.setVisible(False)

        self.spin_paid_amount = QDoubleSpinBox()
        self.spin_paid_amount.setRange(0.0, 10_000_000.0)
        self.spin_paid_amount.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")
        self.spin_paid_amount.setValue(0.0)
        self.spin_paid_amount.setStyleSheet(spin_style)
        self.spin_paid_amount.setVisible(False)  # Only relevant when status = Partial Payment
        self.spin_paid_amount.valueChanged.connect(lambda _: self._refresh_due_display())

        self.lbl_due = QLabel(f"Due: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_due.setStyleSheet("color: #c0392b; font-weight: bold;")

        payment_grid.addWidget(QLabel("Payment Status:"), 0, 0)
        payment_grid.addWidget(self.combo_payment, 0, 1)
        payment_grid.addWidget(self.lbl_payment_field, 0, 2)
        payment_grid.addWidget(self.spin_paid_amount, 0, 3)
        payment_grid.addWidget(self.lbl_due, 0, 4)
        payment_grid.setColumnStretch(5, 1)

        layout.addLayout(payment_grid)
        layout.addSpacing(6)

        # --- Action buttons on their own row, so they can never be pushed off-screen ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        btn_submit = QPushButton("💾 Issue Invoice")
        btn_submit.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; padding: 8px 25px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #27ae60; }")
        btn_submit.clicked.connect(self._on_submit_clicked)

        self.btn_generate_pdf = QPushButton("📄 Download PDF")
        self.btn_generate_pdf.setEnabled(False)
        self.btn_generate_pdf.setStyleSheet("QPushButton { background-color: #3498db; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px; } QPushButton:disabled { background-color: #95a5a6; } QPushButton:hover:!disabled { background-color: #2980b9; }")
        self.btn_generate_pdf.clicked.connect(self._on_generate_pdf_clicked)

        button_layout.addStretch()
        button_layout.addWidget(btn_submit)
        button_layout.addWidget(self.btn_generate_pdf)

        layout.addLayout(button_layout)
        return frame

    # --- Billing helpers -------------------------------------------------
    def _on_payment_status_changed(self, status: str):
        is_partial = status == "Partial Payment"
        self.spin_paid_amount.setVisible(is_partial)
        self.lbl_payment_field.setVisible(is_partial)
        self._refresh_due_display()

    def _refresh_due_display(self):
        status = self.combo_payment.currentText()
        grand_total = self.current_grand_total
        if status == "Paid":
            paid = grand_total
        elif status == "Due":
            paid = 0.0
        else:
            paid = self.spin_paid_amount.value()
        due = max(grand_total - paid, 0.0)
        self.lbl_due.setText(f"Due: {cfg.CURRENCY_SYMBOL} {due:,.2f}")

    def get_discount(self) -> float:
        return self.spin_discount.value()

    def get_tax_rate(self) -> float:
        return self.spin_tax_percent.value() / 100.0

    def get_less_adjustment(self) -> float:
        return self.spin_adjustment.value()

    def get_payment_details(self):
        """Returns (payment_status, paid_amount)."""
        status = self.combo_payment.currentText()
        if status == "Paid":
            paid = self.current_grand_total
        elif status == "Due":
            paid = 0.0
        else:
            paid = self.spin_paid_amount.value()
        return status, paid

    # --- Item cart handlers ------------------------------------------------
    def _on_add_clicked(self):
        product_name = self.combo_product.currentText()
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        self.add_item_requested.emit(product_name, qty, price)

    def _on_remove_clicked(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.remove_item_requested.emit(current_row)
        else:
            QMessageBox.warning(self, "Selection Required", "Please click a row on the item grid to remove first.")

    def _on_submit_clicked(self):
        if not self.txt_cust_name.text().strip() or not self.txt_cust_phone.text().strip():
            QMessageBox.warning(self, "Missing Fields", "Customer Name and Phone Number are strictly required.")
            return

        payment_status, paid_amount = self.get_payment_details()

        if payment_status == "Partial Payment":
            if paid_amount <= 0:
                QMessageBox.warning(self, "Invalid Amount", "Please enter how much has been paid for a partial payment.")
                return
            if paid_amount >= self.current_grand_total:
                QMessageBox.warning(self, "Invalid Amount", "Paid amount must be less than the grand total for a partial payment.")
                return

        self.submit_invoice_requested.emit({
            "customer_name": self.txt_cust_name.text().strip(),
            "customer_phone": self.txt_cust_phone.text().strip(),
            "customer_email": self.txt_cust_email.text().strip(),
            "customer_address": self.txt_cust_address.text().strip(),
            "payment_status": payment_status,
            "discount": self.get_discount(),
            "tax_rate": self.get_tax_rate(),
            "less_adjustment": self.get_less_adjustment(),
            "paid_amount": paid_amount,
        })

    def _on_generate_pdf_clicked(self):
        if self.last_invoice_id is not None:
            self.generate_pdf_requested.emit(self.last_invoice_id)

    def enable_pdf_button(self, invoice_id: int):
        self.last_invoice_id = invoice_id
        self.btn_generate_pdf.setEnabled(True)

    # --- View update hooks called by the controller ------------------------
    def update_items_table(self, items_list: list):
        self.table.setRowCount(0)
        for idx, item in enumerate(items_list):
            self.table.insertRow(idx)
            self.table.setItem(idx, 0, QTableWidgetItem(item['name']))
            self.table.setItem(idx, 1, QTableWidgetItem(f"{item['qty']:.2f} kg"))
            self.table.setItem(idx, 2, QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {item['price']:,.2f}"))
            self.table.setItem(idx, 3, QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {item['subtotal']:,.2f}"))

            for col in [1, 2, 3]:
                self.table.item(idx, col).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def update_metrics(self, subtotal: float, discount: float, tax: float, adjustment: float, grand_total: float):
        self.current_grand_total = grand_total
        self.lbl_subtotal.setText(f"Subtotal: {cfg.CURRENCY_SYMBOL} {subtotal:,.2f}")
        self.lbl_discount_display.setText(f"Discount: {cfg.CURRENCY_SYMBOL} {discount:,.2f}")
        self.lbl_tax.setText(f"VAT: {cfg.CURRENCY_SYMBOL} {tax:,.2f}")
        self.lbl_adjustment_display.setText(f"Less Adj: {cfg.CURRENCY_SYMBOL} {adjustment:,.2f}")
        self.lbl_total.setText(f"Grand Total: {cfg.CURRENCY_SYMBOL} {grand_total:,.2f}")
        self._refresh_due_display()

    def clear_inputs(self):
        self.txt_cust_name.clear()
        self.txt_cust_phone.clear()
        self.txt_cust_email.clear()
        self.txt_cust_address.clear()
        self.spin_qty.setValue(10.0)
        self.spin_price.setValue(25.0)
        self.spin_discount.setValue(0.0)
        self.spin_tax_percent.setValue(0.0)
        self.spin_adjustment.setValue(0.0)
        self.combo_payment.setCurrentIndex(0)  # "Paid"
        self.spin_paid_amount.setValue(0.0)