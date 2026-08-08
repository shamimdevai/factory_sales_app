from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QMessageBox, QCheckBox,
    QSizePolicy
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
    submit_invoice_requested = pyqtSignal(dict)  # Full invoice payload
    generate_pdf_requested = pyqtSignal(int)  # Invoice ID
    customer_selected = pyqtSignal(int)  # customer_id (informational hook)
    add_new_customer_requested = pyqtSignal(dict)  # inline "Add Customer" form submitted

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
        left_panel.addStretch()  # absorbs leftover height so neither card stretches to match the taller right column
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
        # Pin this card to its natural (top-aligned) content height -- without
        # this, the taller "3. Cart Items" card on the right can pull leftover
        # vertical space into this frame, pushing its real content down and
        # leaving a large blank gap under the title.
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl = QLabel("1. Customer Details")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        layout.addWidget(lbl)

        search_row = QHBoxLayout()

        # Editable combo + its built-in QCompleter, tuned for substring/case-
        # insensitive matching -- covers "search by name or phone, autocomplete".
        # The placeholder text IS the instructional label now (no separate
        # QLabel above it -- that was eating an extra row of vertical space).
        self.combo_customer = QComboBox()
        self.combo_customer.setEditable(True)
        self.combo_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_customer.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_customer.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.combo_customer.lineEdit().setPlaceholderText("Search Customer by Name or Phone")
        self.combo_customer.setStyleSheet(theme.input_style("QComboBox"))
        self.combo_customer.setMaximumHeight(34)
        self.combo_customer.currentIndexChanged.connect(self._on_customer_combo_changed)
        search_row.addWidget(self.combo_customer, 1)

        btn_new = QPushButton("+ New")
        btn_new.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2980b9; }")
        btn_new.clicked.connect(self._on_add_new_clicked)
        search_row.addWidget(btn_new)
        layout.addLayout(search_row)

        self.lbl_customer_info = QLabel("")
        self.lbl_customer_info.setStyleSheet(f"border: none; color: {theme.TEXT_MUTED}; font-size: 11px;")
        self.lbl_customer_info.setWordWrap(True)
        self.lbl_customer_info.setVisible(False)
        layout.addWidget(self.lbl_customer_info)

        # --- Inline "Add New Customer" panel (hidden until "+ New" is used) ---
        self.frame_new_customer = QFrame()
        self.frame_new_customer.setStyleSheet(
            f"QFrame {{ background: {theme.PAGE_BACKGROUND}; border: 1px solid {theme.BORDER_COLOR}; border-radius: 6px; }}")
        self.frame_new_customer.setVisible(False)
        new_layout = QVBoxLayout(self.frame_new_customer)
        new_layout.setContentsMargins(10, 10, 10, 10)
        new_layout.setSpacing(6)

        new_title = QLabel("New Customer")
        new_title.setStyleSheet("border: none; font-weight: bold; color: #2c3e50;")
        new_layout.addWidget(new_title)

        new_form = QFormLayout()
        new_form.setSpacing(6)

        input_style = theme.input_style("QLineEdit")
        self.txt_new_name = QLineEdit()
        self.txt_new_phone = QLineEdit()
        self.txt_new_email = QLineEdit()
        self.txt_new_address = QLineEdit()
        for f in [self.txt_new_name, self.txt_new_phone, self.txt_new_email, self.txt_new_address]:
            f.setStyleSheet(input_style)

        self.combo_new_type = QComboBox()
        self.combo_new_type.setStyleSheet(theme.input_style("QComboBox"))

        new_form.addRow("Name *:", self.txt_new_name)
        new_form.addRow("Phone *:", self.txt_new_phone)
        new_form.addRow("Email:", self.txt_new_email)
        new_form.addRow("Address:", self.txt_new_address)
        new_form.addRow("Type:", self.combo_new_type)
        new_layout.addLayout(new_form)

        new_btn_row = QHBoxLayout()
        btn_cancel_new = QPushButton("Cancel")
        btn_cancel_new.clicked.connect(self._on_cancel_new_clicked)
        btn_save_new = QPushButton("Add Customer")
        btn_save_new.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #219653; }")
        btn_save_new.clicked.connect(self._on_submit_new_customer_clicked)
        new_btn_row.addWidget(btn_cancel_new)
        new_btn_row.addStretch()
        new_btn_row.addWidget(btn_save_new)
        new_layout.addLayout(new_btn_row)

        layout.addWidget(self.frame_new_customer)
        return frame

    # --- Customer picker handlers ------------------------------------------
    def _on_customer_combo_changed(self, index: int):
        if index < 0:
            return
        data = self.combo_customer.itemData(index)
        if isinstance(data, dict):
            self.lbl_customer_info.setText(
                f"Phone: {data['phone']}  |  Type: {data['type_name'] or '—'}  |  Status: {data['status_name']}"
            )
            self.lbl_customer_info.setVisible(True)
            self.frame_new_customer.setVisible(False)
            self.customer_selected.emit(data["id"])

    def _on_add_new_clicked(self):
        self.frame_new_customer.setVisible(True)
        self.lbl_customer_info.setVisible(False)
        self.combo_customer.blockSignals(True)
        self.combo_customer.setCurrentIndex(-1)  # back to the placeholder / no selection
        self.combo_customer.blockSignals(False)

    def _on_cancel_new_clicked(self):
        self.frame_new_customer.setVisible(False)
        self.txt_new_name.clear()
        self.txt_new_phone.clear()
        self.txt_new_email.clear()
        self.txt_new_address.clear()
        self.combo_new_type.setCurrentIndex(0)

    def _on_submit_new_customer_clicked(self):
        name = self.txt_new_name.text().strip()
        phone = self.txt_new_phone.text().strip()
        if not name or not phone:
            QMessageBox.warning(self, "Missing Fields", "Name and Phone are required to add a new customer.")
            return
        self.add_new_customer_requested.emit({
            "name": name,
            "phone": phone,
            "email": self.txt_new_email.text().strip(),
            "address": self.txt_new_address.text().strip(),
            "customer_type_id": self.combo_new_type.currentData(),
        })

    # --- Controller-facing data hooks ---------------------------------------
    def populate_customer_list(self, records: list):
        """records: list of dicts {id, name, phone, email, address, type_id,
        type_name, status_name, status_color}, sorted by name. Full record is
        stashed as itemData so selecting an entry needs no extra DB round-trip.
        No "Add New" placeholder item anymore -- the dedicated "+ New" button
        covers that, so the combo just stays on its placeholder until a real
        customer is chosen."""
        self.combo_customer.blockSignals(True)
        self.combo_customer.clear()
        for rec in records:
            self.combo_customer.addItem(f"{rec['name']} — {rec['phone']}", rec)
        self.combo_customer.setCurrentIndex(-1)
        self.combo_customer.blockSignals(False)
        self.lbl_customer_info.setVisible(False)

    def populate_type_choices(self, types: list):
        self.combo_new_type.clear()
        self.combo_new_type.addItem("(None)", None)
        for t in types:
            self.combo_new_type.addItem(t["name"], t["id"])

    def select_customer_by_id(self, customer_id: int):
        for i in range(self.combo_customer.count()):
            data = self.combo_customer.itemData(i)
            if isinstance(data, dict) and data.get("id") == customer_id:
                self.combo_customer.setCurrentIndex(i)  # naturally triggers _on_customer_combo_changed
                return

    def get_selected_customer_id(self):
        data = self.combo_customer.itemData(self.combo_customer.currentIndex())
        return data["id"] if isinstance(data, dict) else None

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
        self.combo_product.setStyleSheet(theme.input_style("QComboBox"))

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

        # Transportation — optional add-on, applied after VAT, before
        # Less Adjustment. Checkbox controls whether the amount field is even usable
        # and whether the row appears on the invoice/PDF at all; unchecked = 0, hidden.
        self.chk_transport = QCheckBox("Transport:")
        self.chk_transport.setStyleSheet(f"""
                    QCheckBox {{
                        color: {theme.TEXT_PRIMARY};
                        spacing: 8px;
                        font-weight: 500;
                        padding: 5px 10px;
                        border: 1px solid {theme.BORDER_COLOR};
                        border-radius: 4px;
                        background: {theme.CARD_BACKGROUND};
                    }}
                    QCheckBox:hover {{
                        border-color: {theme.ACCENT};
                    }}
                    QCheckBox::indicator {{
                        width: 16px;
                        height: 16px;
                        border: 2px solid {theme.BORDER_COLOR};
                        border-radius: 3px;
                        background: {theme.CARD_BACKGROUND};
                    }}
                    QCheckBox::indicator:checked {{
                        background-color: {theme.ACCENT};
                        border-color: {theme.ACCENT_DARK};
                    }}
                """)
        self.chk_transport.toggled.connect(self._on_transport_toggle)

        self.spin_transport = QDoubleSpinBox()
        self.spin_transport.setRange(0.0, 10_000_000.0)
        self.spin_transport.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")
        self.spin_transport.setValue(0.0)
        self.spin_transport.setStyleSheet(spin_style)
        self.spin_transport.setVisible(False)  # only usable once the checkbox is checked
        self.spin_transport.valueChanged.connect(lambda _: self.billing_changed.emit())

        billing_grid.addWidget(QLabel("Discount:"), 0, 0)
        billing_grid.addWidget(self.spin_discount, 0, 1)
        billing_grid.addWidget(QLabel("VAT:"), 0, 2)
        billing_grid.addWidget(self.spin_tax_percent, 0, 3)
        # Transport before Less Adj, same row — matches the field order used
        # in the calculation (transport applied before less_adjustment).
        billing_grid.addWidget(self.chk_transport, 1, 0)
        billing_grid.addWidget(self.spin_transport, 1, 1)
        billing_grid.addWidget(QLabel("Less Adj:"), 1, 2)
        billing_grid.addWidget(self.spin_adjustment, 1, 3)
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
        self.lbl_transport_display = QLabel(f"Transport: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_adjustment_display = QLabel(f"Less Adj: {cfg.CURRENCY_SYMBOL} 0.00")
        self.lbl_total = QLabel(f"Grand Total: {cfg.CURRENCY_SYMBOL} 0.00")

        metric_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        for label in [self.lbl_subtotal, self.lbl_discount_display, self.lbl_tax,
                      self.lbl_transport_display, self.lbl_adjustment_display, self.lbl_total]:
            label.setFont(metric_font)
            label.setStyleSheet("color: #2c3e50;")

        # Row 0: Subtotal, Discount, VAT
        # Row 1: Transport, Less Adj, Grand Total (Grand Total last, as requested)
        metrics_grid.addWidget(self.lbl_subtotal, 0, 0)
        metrics_grid.addWidget(self.lbl_discount_display, 0, 1)
        metrics_grid.addWidget(self.lbl_tax, 0, 2)
        metrics_grid.addWidget(self.lbl_transport_display, 1, 0)
        metrics_grid.addWidget(self.lbl_adjustment_display, 1, 1)
        metrics_grid.addWidget(self.lbl_total, 1, 2)

        layout.addLayout(metrics_grid)
        layout.addSpacing(4)

        # --- Payment info row (its own grid, buttons on a separate row below) ---
        payment_grid = QGridLayout()
        payment_grid.setHorizontalSpacing(10)
        payment_grid.setVerticalSpacing(8)

        self.combo_payment = QComboBox()
        self.combo_payment.addItems(["Paid", "Due", "Partial Payment"])
        self.combo_payment.setStyleSheet(theme.input_style("QComboBox"))
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
    def _on_transport_toggle(self, checked: bool):
        self.spin_transport.setVisible(checked)
        if not checked:
            self.spin_transport.setValue(0.0)
        self.billing_changed.emit()

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

    def is_transport_charge_shown(self) -> bool:
        return self.chk_transport.isChecked()

    def get_transport_charge(self) -> float:
        return self.spin_transport.value() if self.chk_transport.isChecked() else 0.0

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
        customer_id = self.get_selected_customer_id()
        if not customer_id:
            QMessageBox.warning(self, "Customer Required", "Please select an existing customer or add a new one before issuing the invoice.")
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
            "customer_id": customer_id,
            "payment_status": payment_status,
            "discount": self.get_discount(),
            "tax_rate": self.get_tax_rate(),
            "less_adjustment": self.get_less_adjustment(),
            "transport_charge": self.get_transport_charge(),
            "show_transport_charge": self.is_transport_charge_shown(),
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

    def update_metrics(self, subtotal: float, discount: float, tax: float, transport: float, adjustment: float, grand_total: float):
        self.current_grand_total = grand_total
        self.lbl_subtotal.setText(f"Subtotal: {cfg.CURRENCY_SYMBOL} {subtotal:,.2f}")
        self.lbl_discount_display.setText(f"Discount: {cfg.CURRENCY_SYMBOL} {discount:,.2f}")
        self.lbl_tax.setText(f"VAT: {cfg.CURRENCY_SYMBOL} {tax:,.2f}")
        self.lbl_transport_display.setText(f"Transport: {cfg.CURRENCY_SYMBOL} {transport:,.2f}")
        self.lbl_adjustment_display.setText(f"Less Adj: {cfg.CURRENCY_SYMBOL} {adjustment:,.2f}")
        self.lbl_total.setText(f"Grand Total: {cfg.CURRENCY_SYMBOL} {grand_total:,.2f}")
        self._refresh_due_display()

    def clear_inputs(self):
        self.combo_customer.blockSignals(True)
        self.combo_customer.setCurrentIndex(-1)
        self.combo_customer.blockSignals(False)
        self.lbl_customer_info.setVisible(False)
        self.frame_new_customer.setVisible(False)
        self.spin_qty.setValue(10.0)
        self.spin_price.setValue(25.0)
        self.spin_discount.setValue(0.0)
        self.spin_tax_percent.setValue(0.0)
        self.spin_adjustment.setValue(0.0)
        self.chk_transport.setChecked(False)
        self.spin_transport.setValue(0.0)
        self.combo_payment.setCurrentIndex(0)  # "Paid"
        self.spin_paid_amount.setValue(0.0)