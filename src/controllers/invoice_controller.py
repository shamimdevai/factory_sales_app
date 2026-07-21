from PyQt6.QtWidgets import QMessageBox, QFileDialog
from src.database.connection import get_db_session
from src.database.models import Customer, Invoice, InvoiceItem, User
from src.views.invoice_view import InvoiceView
from src.utils.pdf_generator import PDFGenerator
from src.config import company_config as cfg


class InvoiceController:
    def __init__(self, view: InvoiceView):
        self.view = view
        self.cart_items = []  # Keep track of added items in memory

        self.view.add_item_requested.connect(self.add_item_to_cart)
        self.view.remove_item_requested.connect(self.remove_item_from_cart)
        self.view.billing_changed.connect(self._sync_view_data)
        self.view.submit_invoice_requested.connect(self.commit_invoice)
        self.view.generate_pdf_requested.connect(self.generate_invoice_pdf)

    def add_item_to_cart(self, name: str, qty: float, price: float):
        subtotal = qty * price
        self.cart_items.append({
            "name": name,
            "qty": qty,
            "price": price,
            "subtotal": subtotal
        })
        self._sync_view_data()

    def remove_item_from_cart(self, row_index: int):
        if 0 <= row_index < len(self.cart_items):
            self.cart_items.pop(row_index)
            self._sync_view_data()

    def _sync_view_data(self):
        subtotal = sum(item["subtotal"] for item in self.cart_items)
        discount = self.view.get_discount()
        tax_rate = self.view.get_tax_rate()
        adjustment = self.view.get_less_adjustment()

        taxable_amount = max(subtotal - discount, 0.0)
        tax = taxable_amount * tax_rate
        grand_total = max(taxable_amount + tax - adjustment, 0.0)

        self.view.update_items_table(self.cart_items)
        self.view.update_metrics(subtotal, discount, tax, adjustment, grand_total)

    def commit_invoice(self, data: dict):
        if not self.cart_items:
            QMessageBox.warning(self.view, "Empty Cart", "Please add items to your cart before issuing an invoice.")
            return

        try:
            with get_db_session() as session:
                # 1. Fetch or create Customer
                customer = session.query(Customer).filter_by(phone=data["customer_phone"]).first()
                if not customer:
                    customer = Customer(name=data["customer_name"], phone=data["customer_phone"],
                                         email=data["customer_email"], address=data["customer_address"])
                    session.add(customer)
                    session.flush()
                else:
                    customer.name = data["customer_name"]
                    customer.email = data["customer_email"]
                    customer.address = data["customer_address"]

                # 2. Get active user or fallback operator
                active_user = session.query(User).first()
                if not active_user:
                    active_user = User(
                        name="System Operator",
                        username="admin",
                        email="admin@factory.com",
                        password_hash="system_fallback"
                    )
                    session.add(active_user)
                    session.flush()

                # 3. Financial calculations
                subtotal = sum(item["subtotal"] for item in self.cart_items)
                discount = max(data.get("discount", 0.0), 0.0)
                tax_rate = max(data.get("tax_rate", 0.0), 0.0)
                adjustment = max(data.get("less_adjustment", 0.0), 0.0)
                taxable_amount = max(subtotal - discount, 0.0)
                tax_amount = taxable_amount * tax_rate
                grand_total = max(taxable_amount + tax_amount - adjustment, 0.0)
                paid_amount = max(data.get("paid_amount", 0.0), 0.0)

                # 4. Save Invoice Document
                invoice = Invoice(
                    customer_id=customer.id,
                    user_id=active_user.id,
                    total_amount=subtotal,
                    discount_amount=discount,
                    tax_rate=tax_rate,
                    less_adjustment=adjustment,
                    grand_total=grand_total,
                    paid_amount=paid_amount,
                    payment_status=data["payment_status"]
                )
                session.add(invoice)
                session.flush()

                # 5. Save Invoice Items
                for cart_item in self.cart_items:
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        product_name=cart_item["name"],
                        quantity=cart_item["qty"],
                        unit_price=cart_item["price"],
                        subtotal=cart_item["subtotal"]
                    )
                    session.add(item)

                session.commit()

                QMessageBox.information(
                    self.view, "Success",
                    f"Invoice #{invoice.id} issued successfully!\nTotal: {cfg.CURRENCY_SYMBOL} {grand_total:,.2f}"
                )

                # Reset State
                self.cart_items.clear()
                self._sync_view_data()
                self.view.clear_inputs()
                self.view.enable_pdf_button(invoice.id)

        except Exception as e:
            QMessageBox.critical(self.view, "Database Error", f"Failed to save invoice: {str(e)}")

    @staticmethod
    def record_due_payment(root_invoice_id: int, amount: float) -> int:
        """
        Creates a due-payment record linked to `root_invoice_id`. This is NOT a product
        sale — no cart items, no subtotal/tax — just an amount received against the
        original invoice's outstanding balance. The original invoice row is never
        modified; the running due balance is always derived dynamically via
        Invoice.effective_due_amount / effective_paid_amount / effective_status.

        Returns the newly created due-payment invoice's id. Raises ValueError on
        validation failures so callers can surface a QMessageBox with the message.
        """
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        with get_db_session() as session:
            root = session.query(Invoice).filter_by(id=root_invoice_id, is_due_payment=False).first()
            if not root:
                raise ValueError(f"Original invoice #{root_invoice_id} not found.")

            current_due = root.effective_due_amount
            if current_due <= 0:
                raise ValueError(f"Invoice #{root_invoice_id} has no outstanding due balance.")
            if amount > current_due + 0.01:  # small float-safety tolerance
                raise ValueError(
                    f"Payment amount ({amount:,.2f}) exceeds the current due balance ({current_due:,.2f})."
                )

            due_payment = Invoice(
                customer_id=root.customer_id,
                user_id=root.user_id,
                total_amount=0.0,
                discount_amount=0.0,
                tax_rate=0.0,
                less_adjustment=0.0,
                grand_total=0.0,
                paid_amount=amount,
                payment_status="Paid",  # this transaction itself is a completed payment
                parent_invoice_id=root.id,
                is_due_payment=True,
            )
            session.add(due_payment)
            session.commit()
            session.refresh(due_payment)
            return due_payment.id

    def generate_invoice_pdf(self, invoice_id: int):
        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save Invoice PDF", f"Invoice_{invoice_id}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        if PDFGenerator.generate_invoice_pdf(invoice_id, file_path):
            QMessageBox.information(self.view, "Success", f"Invoice #{invoice_id} PDF saved successfully!")
        else:
            QMessageBox.critical(self.view, "Error", "Failed to compile the dynamic PDF layout.")