from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDoubleSpinBox,
    QSpinBox, QFormLayout, QFrame, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from src.config import theme
from src.config import company_config as cfg


# --- Local one-off semantic button colors (per Rule 9 -- not centralized) ---
_EDIT_BTN = "QPushButton { background-color: #3498db; color: white; border-radius: 3px; } QPushButton:hover { background-color: #2980b9; }"
_DELETE_BTN = "QPushButton { background-color: #e74c3c; color: white; border-radius: 3px; } QPushButton:hover { background-color: #c0392b; }"
_MOVE_BTN = "QPushButton { background-color: #95a5a6; color: white; border-radius: 3px; } QPushButton:hover { background-color: #7f8c8d; } QPushButton:disabled { background-color: #d5dbdb; color: #aab2b3; }"
_SAVE_BTN = "QPushButton { background-color: #27ae60; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #219653; }"
_ADD_BTN = f"QPushButton {{ background-color: {theme.ACCENT}; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background-color: {theme.ACCENT_DARK}; }}"


class TierDialog(QDialog):
    """Add/Edit a Status tier (Silver/Golden/Platinum/...). Pure GUI -- no DB access."""

    def __init__(self, parent, name: str = "", min_amount: float = 0.0, period: str = "monthly"):
        super().__init__(parent)
        self.setWindowTitle("Status Tier")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.txt_name = QLineEdit(name)
        self.txt_name.setStyleSheet(theme.input_style("QLineEdit"))
        form.addRow("Status Name:", self.txt_name)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100_000_000.0)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setValue(max(min_amount, 0.01))
        self.spin_amount.setStyleSheet(theme.input_style("QDoubleSpinBox"))
        form.addRow("Min. Purchase Amount:", self.spin_amount)

        self.combo_period = QComboBox()
        self.combo_period.addItem("Monthly", "monthly")
        self.combo_period.addItem("Yearly", "yearly")
        self.combo_period.setCurrentIndex(0 if period == "monthly" else 1)
        self.combo_period.setStyleSheet(theme.input_style("QComboBox"))
        form.addRow("Evaluation Period:", self.combo_period)

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
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Please enter a name for this Status tier.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.txt_name.text().strip(),
            "min_amount": self.spin_amount.value(),
            "period": self.combo_period.currentData(),
        }


class TypeDialog(QDialog):
    """Add/Edit a Customer Type. Pure GUI -- no DB access."""

    def __init__(self, parent, name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Customer Type")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Type Name:"))
        self.txt_name = QLineEdit(name)
        self.txt_name.setStyleSheet(theme.input_style("QLineEdit"))
        layout.addWidget(self.txt_name)

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
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Please enter a type name.")
            return
        self.accept()

    def get_name(self) -> str:
        return self.txt_name.text().strip()


class ProductDialog(QDialog):
    """Add/Edit a Product catalog entry (name, unit, default price). Pure GUI -- no DB access."""

    _COMMON_UNITS = ["kg", "g", "L", "ml", "pcs", "box", "bag", "ton"]

    def __init__(self, parent, name: str = "", unit: str = "kg", default_price: float = 0.0):
        super().__init__(parent)
        self.setWindowTitle("Product")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.txt_name = QLineEdit(name)
        self.txt_name.setStyleSheet(theme.input_style("QLineEdit"))
        form.addRow("Product Name:", self.txt_name)

        # Editable combo: pick a common unit or type a custom one (e.g. "bag", "ton").
        self.combo_unit = QComboBox()
        self.combo_unit.setEditable(True)
        self.combo_unit.addItems(self._COMMON_UNITS)
        if unit and unit not in self._COMMON_UNITS:
            self.combo_unit.addItem(unit)
        self.combo_unit.setCurrentText(unit or "kg")
        self.combo_unit.setStyleSheet(theme.input_style("QComboBox"))
        form.addRow("Unit:", self.combo_unit)

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 100_000_000.0)
        self.spin_price.setDecimals(2)
        self.spin_price.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")
        self.spin_price.setValue(max(default_price, 0.01))
        self.spin_price.setStyleSheet(theme.input_style("QDoubleSpinBox"))
        form.addRow("Default Unit Price:", self.spin_price)

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
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Missing Name", "Please enter a product name.")
            return
        if not self.combo_unit.currentText().strip():
            QMessageBox.warning(self, "Missing Unit", "Please enter or select a unit.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.txt_name.text().strip(),
            "unit": self.combo_unit.currentText().strip(),
            "default_price": self.spin_price.value(),
        }


class SettingsView(QWidget):
    # Status tiers
    add_tier_requested = pyqtSignal()
    edit_tier_requested = pyqtSignal(int)     # tier id
    delete_tier_requested = pyqtSignal(int)   # tier id
    move_tier_up_requested = pyqtSignal(int)      # tier id
    move_tier_down_requested = pyqtSignal(int)    # tier id

    # Customer types
    add_type_requested = pyqtSignal()
    edit_type_requested = pyqtSignal(int)  # type id
    delete_type_requested = pyqtSignal(int)  # type id

    # Products
    add_product_requested = pyqtSignal()
    edit_product_requested = pyqtSignal(int)  # product id
    delete_product_requested = pyqtSignal(int)  # product id

    # Status rules
    save_rules_requested = pyqtSignal(int, int, int)  # grace_days, decay_step_days, rank_hold_months

    def __init__(self):
        super().__init__()
        # self.setMinimumWidth(700)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        self.main_layout.addWidget(title)

        self.main_layout.addWidget(self._create_tiers_box())
        self.main_layout.addWidget(self._create_types_box())
        self.main_layout.addWidget(self._create_products_box())
        self.main_layout.addWidget(self._create_rules_box())
        self.main_layout.addStretch()

        self._header_button_filter = theme.install_responsive_buttons(self, [
            (self.btn_add_tier, "+ Add Status Tier", "+"),
            (self.btn_add_type, "+ Add Type", "+"),
            (self.btn_add_product, "+ Add Product", "+"),
        ])

    # ---------------- Status Tiers ----------------
    def _create_tiers_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        header_row = QHBoxLayout()
        lbl = QLabel("Customer Status Tiers")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        header_row.addWidget(lbl)
        header_row.addStretch()
        self.btn_add_tier = QPushButton("+ Add Status Tier")
        self.btn_add_tier.setStyleSheet(_ADD_BTN)
        self.btn_add_tier.clicked.connect(self.add_tier_requested.emit)
        header_row.addWidget(self.btn_add_tier)
        layout.addLayout(header_row)

        note = QLabel("Order below = evaluation priority, highest first. Use ▲▼ to reorder.")
        note.setStyleSheet(f"border: none; color: {theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(note)

        self.table_tiers = QTableWidget()
        theme.configure_responsive_table(self.table_tiers, [
            (160, "stretch"), (130, "stretch"), (90, "stretch"),
            (90, "fixed"), (90, "fixed"),
        ])
        self.table_tiers.setHorizontalHeaderLabels(["Status Name", "Min. Amount", "Period", "Reorder", "Actions"])
        self.table_tiers.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_tiers.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_tiers.setMinimumHeight(160)
        layout.addWidget(self.table_tiers)

        return frame

    def populate_tiers(self, tiers: list):
        """tiers: list of dicts, ORDERED highest rank (evaluated first) to lowest,
        each: {id, name, min_amount, period}"""
        self.table_tiers.setRowCount(len(tiers))
        for row, tier in enumerate(tiers):
            self.table_tiers.setItem(row, 0, QTableWidgetItem(tier["name"]))
            self.table_tiers.setItem(row, 1, QTableWidgetItem(f"{tier['min_amount']:,.2f}"))
            self.table_tiers.setItem(row, 2, QTableWidgetItem(tier["period"].capitalize()))

            reorder_widget = QWidget()
            reorder_layout = QHBoxLayout(reorder_widget)
            reorder_layout.setContentsMargins(2, 2, 2, 2)
            reorder_layout.setSpacing(3)
            btn_up = QPushButton("▲")
            btn_down = QPushButton("▼")
            btn_up.setStyleSheet(_MOVE_BTN)
            btn_down.setStyleSheet(_MOVE_BTN)
            btn_up.setFixedWidth(30)
            btn_down.setFixedWidth(30)
            btn_up.setEnabled(row > 0)
            btn_down.setEnabled(row < len(tiers) - 1)
            btn_up.clicked.connect(lambda checked, tid=tier["id"]: self.move_tier_up_requested.emit(tid))
            btn_down.clicked.connect(lambda checked, tid=tier["id"]: self.move_tier_down_requested.emit(tid))
            reorder_layout.addWidget(btn_up)
            reorder_layout.addWidget(btn_down)
            self.table_tiers.setCellWidget(row, 3, reorder_widget)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(3)
            btn_edit = QPushButton("✏️")
            btn_delete = QPushButton("🗑️")
            btn_edit.setStyleSheet(_EDIT_BTN)
            btn_delete.setStyleSheet(_DELETE_BTN)
            btn_edit.setFixedWidth(30)
            btn_delete.setFixedWidth(30)
            btn_edit.clicked.connect(lambda checked, tid=tier["id"]: self.edit_tier_requested.emit(tid))
            btn_delete.clicked.connect(lambda checked, tid=tier["id"]: self.delete_tier_requested.emit(tid))
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_delete)
            self.table_tiers.setCellWidget(row, 4, actions_widget)

    # ---------------- Customer Types ----------------
    def _create_types_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        header_row = QHBoxLayout()
        lbl = QLabel("Customer Types")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        header_row.addWidget(lbl)
        header_row.addStretch()
        self.btn_add_type = QPushButton("+ Add Type")
        self.btn_add_type.setStyleSheet(_ADD_BTN)
        self.btn_add_type.clicked.connect(self.add_type_requested.emit)
        header_row.addWidget(self.btn_add_type)
        layout.addLayout(header_row)

        self.table_types = QTableWidget()
        theme.configure_responsive_table(self.table_types, [
            (200, "stretch"), (90, "fixed"),
        ])
        self.table_types.setHorizontalHeaderLabels(["Type Name", "Actions"])
        self.table_types.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_types.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_types.setMinimumHeight(140)
        layout.addWidget(self.table_types)

        return frame

    def populate_types(self, types: list):
        """types: list of dicts: {id, name}"""
        self.table_types.setRowCount(len(types))
        for row, t in enumerate(types):
            self.table_types.setItem(row, 0, QTableWidgetItem(t["name"]))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(3)
            btn_edit = QPushButton("✏️")
            btn_delete = QPushButton("🗑️")
            btn_edit.setStyleSheet(_EDIT_BTN)
            btn_delete.setStyleSheet(_DELETE_BTN)
            btn_edit.setFixedWidth(30)
            btn_delete.setFixedWidth(30)
            btn_edit.clicked.connect(lambda checked, tid=t["id"]: self.edit_type_requested.emit(tid))
            btn_delete.clicked.connect(lambda checked, tid=t["id"]: self.delete_type_requested.emit(tid))
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_delete)
            self.table_types.setCellWidget(row, 1, actions_widget)

    # ---------------- Products ----------------
    def _create_products_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        header_row = QHBoxLayout()
        lbl = QLabel("Products")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        header_row.addWidget(lbl)
        header_row.addStretch()
        self.btn_add_product = QPushButton("+ Add Product")
        self.btn_add_product.setStyleSheet(_ADD_BTN)
        self.btn_add_product.clicked.connect(self.add_product_requested.emit)
        header_row.addWidget(self.btn_add_product)
        layout.addLayout(header_row)

        note = QLabel(
            "Shown in the Invoice Terminal's product dropdown. Unit/Price pre-fill the sale form but stay editable per invoice.")
        note.setStyleSheet(f"border: none; color: {theme.TEXT_MUTED}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.table_products = QTableWidget()
        theme.configure_responsive_table(self.table_products, [
            (200, "stretch"), (90, "fixed"), (140, "stretch"), (90, "fixed"),
        ])
        self.table_products.setHorizontalHeaderLabels(["Product Name", "Unit", "Default Price", "Actions"])
        self.table_products.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_products.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_products.setMinimumHeight(140)
        layout.addWidget(self.table_products)

        return frame

    def populate_products(self, products: list):
        """products: list of dicts: {id, name, unit, default_price}"""
        self.table_products.setRowCount(len(products))
        for row, p in enumerate(products):
            self.table_products.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.table_products.setItem(row, 1, QTableWidgetItem(p["unit"]))
            self.table_products.setItem(row, 2,
                                            QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {p['default_price']:,.2f}"))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(3)
            btn_edit = QPushButton("✏️")
            btn_delete = QPushButton("🗑️")
            btn_edit.setStyleSheet(_EDIT_BTN)
            btn_delete.setStyleSheet(_DELETE_BTN)
            btn_edit.setFixedWidth(30)
            btn_delete.setFixedWidth(30)
            btn_edit.clicked.connect(lambda checked, pid=p["id"]: self.edit_product_requested.emit(pid))
            btn_delete.clicked.connect(lambda checked, pid=p["id"]: self.delete_product_requested.emit(pid))
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_delete)
            self.table_products.setCellWidget(row, 3, actions_widget)


    # ---------------- Status Rules ----------------
    def _create_rules_box(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(theme.card_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl = QLabel("Status Rules")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        layout.addWidget(lbl)

        note = QLabel(
            "Grace Period: days after a due invoice before any Status penalty starts.\n"
            "Decay Step: extra days per additional Status downgrade after grace expires.\n"
            "Hold Period: months a customer keeps an earned Status before it re-evaluates down."
        )
        note.setStyleSheet(f"border: none; color: {theme.TEXT_MUTED}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(8)

        self.spin_grace = QSpinBox()
        self.spin_grace.setRange(1, 3650)
        self.spin_grace.setSuffix(" days")
        self.spin_grace.setStyleSheet(theme.input_style("QSpinBox"))
        form.addRow("Grace Period:", self.spin_grace)

        self.spin_decay = QSpinBox()
        self.spin_decay.setRange(1, 3650)
        self.spin_decay.setSuffix(" days")
        self.spin_decay.setStyleSheet(theme.input_style("QSpinBox"))
        form.addRow("Decay Step:", self.spin_decay)

        self.spin_hold = QSpinBox()
        self.spin_hold.setRange(1, 120)
        self.spin_hold.setSuffix(" months")
        self.spin_hold.setStyleSheet(theme.input_style("QSpinBox"))
        form.addRow("Status Hold Period:", self.spin_hold)

        layout.addLayout(form)

        btn_save = QPushButton("Save Status Rules")
        btn_save.setStyleSheet(_SAVE_BTN)
        btn_save.clicked.connect(
            lambda: self.save_rules_requested.emit(
                self.spin_grace.value(), self.spin_decay.value(), self.spin_hold.value()
            )
        )
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignRight)

        return frame

    def populate_rules(self, grace_days: int, decay_step_days: int, rank_hold_months: int):
        self.spin_grace.setValue(grace_days)
        self.spin_decay.setValue(decay_step_days)
        self.spin_hold.setValue(rank_hold_months)