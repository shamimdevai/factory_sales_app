from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDoubleSpinBox,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from src.config import company_config as cfg
from src.config import theme


class DuePaymentDialog(QDialog):
    """Collects a payment amount against an invoice's current outstanding due balance.
    Pure GUI — no DB access here; the controller supplies the figures and reads the result."""

    def __init__(self, parent, invoice_id: int, customer_name: str,
                 grand_total: float, paid_so_far: float, due_amount: float):
        super().__init__(parent)
        self.setWindowTitle(f"Record Due Payment — Invoice #{invoice_id}")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Invoice #{invoice_id} — {customer_name}")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border-radius: 6px; }")
        info_layout = QVBoxLayout(info_frame)
        info_layout.addWidget(QLabel(f"Grand Total: {cfg.CURRENCY_SYMBOL} {grand_total:,.2f}"))
        info_layout.addWidget(QLabel(f"Paid So Far: {cfg.CURRENCY_SYMBOL} {paid_so_far:,.2f}"))
        due_label = QLabel(f"Current Due: {cfg.CURRENCY_SYMBOL} {due_amount:,.2f}")
        due_label.setStyleSheet("color: #c0392b; font-weight: bold;")
        info_layout.addWidget(due_label)
        layout.addWidget(info_frame)

        layout.addWidget(QLabel("Amount received now:"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, max(due_amount, 0.01))
        self.amount_spin.setDecimals(2)
        self.amount_spin.setPrefix(f"{cfg.CURRENCY_SYMBOL} ")
        self.amount_spin.setValue(due_amount)  # default to full remaining due
        self.amount_spin.setStyleSheet(theme.input_style("QDoubleSpinBox"))
        layout.addWidget(self.amount_spin)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Record Payment")
        btn_ok.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #219653; }")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def get_amount(self) -> float:
        return self.amount_spin.value()


class PaymentHistoryDialog(QDialog):
    """Shows the full chain (original invoice + every linked due-payment) for one invoice.
    Each row can be reprinted individually as its own PDF."""

    reprint_requested = pyqtSignal(int)  # emits the record's invoice id (root or due-payment)

    def __init__(self, parent, root_invoice_id: int, customer_name: str, chain: list):
        super().__init__(parent)
        self.setWindowTitle(f"Payment History — Invoice #{root_invoice_id}")
        self.setMinimumSize(520, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Payment Chain — Invoice #{root_invoice_id} ({customer_name})")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Record", "Date", "Amount", "PDF"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 130)
        table.setColumnWidth(2, 110)
        table.setColumnWidth(3, 60)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setRowCount(len(chain))

        for row, record in enumerate(chain):
            table.setItem(row, 0, QTableWidgetItem(record["label"]))
            table.setItem(row, 1, QTableWidgetItem(record["date"]))
            amount_item = QTableWidgetItem(f"{cfg.CURRENCY_SYMBOL} {record['amount']:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, 2, amount_item)

            btn = QPushButton("📄")
            btn.setToolTip("Download PDF for this record")
            btn.setStyleSheet(
                "QPushButton { background-color: #3498db; color: white; font-size: 11px; border-radius: 3px; } QPushButton:hover { background-color: #2980b9; }")
            btn.clicked.connect(lambda checked, rec_id=record["id"]: self.reprint_requested.emit(rec_id))
            table.setCellWidget(row, 3, btn)

        layout.addWidget(table)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)