from src.database.connection import get_db_session
from src.database.models import Invoice, Customer
from src.views.history_view import HistoryView
from src.views.due_payment_dialog import DuePaymentDialog, PaymentHistoryDialog
from src.utils.excel_exporter import ExcelExporter
from src.utils.pdf_generator import PDFGenerator
from src.controllers.invoice_controller import InvoiceController
from src.config import company_config as cfg
from PyQt6.QtWidgets import QMessageBox, QFileDialog

class HistoryController:
    def __init__(self, view: HistoryView):
        self.view = view
        self._last_filter = None  # remembered filter dict — reused to refresh after a due payment
        self.view.search_requested.connect(self.load_records)
        self.view.export_excel_requested.connect(self.export_to_excel)
        self.view.export_pdf_requested.connect(self.export_to_summary_pdf)
        self.view.reprint_invoice_requested.connect(self.reprint_single_invoice)
        self.view.pay_due_requested.connect(self.handle_pay_due)
        self.view.view_payment_history_requested.connect(self.handle_view_payment_history)

    def show_customer_ledger(self, customer_id: int, customer_name: str):
        """Entry point for cross-page navigation (Customers page's 'View Ledger'
        button). main_window.py switches the visible page to History; this just
        applies the filter once it's shown."""
        self.view.apply_customer_filter(customer_id, customer_name)

    def _get_filtered_records(self, filter_dict: dict) -> list:
        """
        Supports these filter modes:
          - "quick_search": {"value": "..."}  — live, matches ACROSS Invoice ID,
                             Customer Name, Phone, Date, effective Status, Grand
                             Total, and effective Due, all at once. Empty value
                             -> every record (the default/no-filter state).
          - "date":          {"start": QDate, "end": QDate}
          - "status":        {"value": "Due"}         — matched against the EFFECTIVE status
          - "customer_id":   {"customer_id": 7}        — exact match, used only via
                              apply_customer_filter() (Customers page "View Ledger")
        "status" and "quick_search" match against effective_status / effective_due_amount,
        which are computed properties (not DB columns), so both filter in Python
        after loading candidates rather than in SQL.
        Only root/original sale invoices are returned — due-payment records stay nested
        (accessible via the "History" action), same as before.

        All ordering/filtering/display here is driven by invoice_date (the
        business/purchase date) rather than created_at (the true DB-insert
        timestamp) — a backdated invoice sorts, filters, and displays under
        its real transaction date, not the day it happened to be typed in.
        """
        mode = filter_dict.get("mode", "quick_search")

        with get_db_session() as session:
            base_query = session.query(Invoice).join(Customer).filter(Invoice.is_due_payment == False)

            if mode == "quick_search":
                value = (filter_dict.get("value") or "").strip().lower()
                candidates = base_query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()
                if not value:
                    invoices = candidates
                else:
                    invoices = []
                    for inv in candidates:
                        haystack = " ".join([
                            str(inv.id),
                            inv.customer.name or "",
                            inv.customer.phone or "",
                            inv.invoice_date.strftime("%Y-%m-%d"),
                            inv.effective_status,
                            f"{inv.grand_total:.2f}",
                            f"{inv.effective_due_amount:.2f}",
                        ]).lower()
                        if value in haystack:
                            invoices.append(inv)

            elif mode == "date":
                start_date = filter_dict["start"].toPyDate()
                end_date = filter_dict["end"].toPyDate()
                invoices = base_query.filter(
                    Invoice.invoice_date.between(start_date, end_date)
                ).order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()

            elif mode == "status":
                value = filter_dict.get("value", "")
                candidates = base_query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()
                invoices = [inv for inv in candidates if inv.effective_status == value]

            elif mode == "customer_id":
                customer_id = filter_dict.get("customer_id")
                if not customer_id:
                    raise ValueError("Invalid customer filter.")
                invoices = base_query.filter(
                    Invoice.customer_id == customer_id
                ).order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()

            else:
                invoices = []

            return [{
                "id": inv.id,
                "customer_name": inv.customer.name,
                "date": inv.invoice_date.strftime("%Y-%m-%d"),
                "discount": inv.discount_amount,
                "grand_total": inv.grand_total,
                "due": inv.effective_due_amount,
                "status": inv.effective_status,
                "has_due_payments": len(inv.due_payments) > 0,
            } for inv in invoices]

    def load_records(self, filter_dict: dict):
        self._last_filter = filter_dict
        try:
            records = self._get_filtered_records(filter_dict)
            self.view.populate_table(records)
        except ValueError as ve:
            QMessageBox.warning(self.view, "Invalid Search", str(ve))
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Could not query history data: {e}")

    def _refresh(self):
        if self._last_filter:
            self.load_records(self._last_filter)

    def export_to_excel(self, filter_dict: dict, filepath: str):
        try:
            records = self._get_filtered_records(filter_dict)
            if not records:
                QMessageBox.warning(self.view, "No Data", "No transaction records found for this filter.")
                return
            if ExcelExporter.export_sales_ledger(records, filepath):
                QMessageBox.information(self.view, "Success", "Excel Ledger written successfully!")
        except ValueError as ve:
            QMessageBox.warning(self.view, "Invalid Search", str(ve))
        except Exception as e:
            QMessageBox.critical(self.view, "Export Failed", str(e))

    def export_to_summary_pdf(self, filter_dict: dict, filepath: str):
        try:
            records = self._get_filtered_records(filter_dict)
            if not records:
                QMessageBox.warning(self.view, "No Data", "No transaction records found for this filter.")
                return
            if PDFGenerator.generate_summary_pdf(records, filepath):
                QMessageBox.information(self.view, "Success", "Summary Ledger PDF saved successfully!")
        except ValueError as ve:
            QMessageBox.warning(self.view, "Invalid Search", str(ve))
        except Exception as e:
            QMessageBox.critical(self.view, "Export Failed", str(e))

    def reprint_single_invoice(self, invoice_id: int, filepath: str):
        if PDFGenerator.generate_invoice_pdf(invoice_id, filepath):
            QMessageBox.information(self.view, "Success", f"Invoice #{invoice_id} saved successfully!")
        else:
            QMessageBox.critical(self.view, "Error", "Failed to compile the dynamic PDF layout.")

    def handle_pay_due(self, invoice_id: int):
        """Opens the due-payment dialog for a root invoice, records the payment, then
        prompts to save a PDF receipt for it."""
        try:
            with get_db_session() as session:
                invoice = session.query(Invoice).filter_by(id=invoice_id, is_due_payment=False).first()
                if invoice:
                    customer_name = invoice.customer.name
                    grand_total = invoice.grand_total
                    paid_so_far = invoice.effective_paid_amount
                    due_amount = invoice.effective_due_amount
                else:
                    customer_name = None

            if customer_name is None:
                QMessageBox.critical(self.view, "Error", f"Invoice #{invoice_id} not found.")
                return

            if due_amount <= 0:
                QMessageBox.information(self.view, "No Due", f"Invoice #{invoice_id} has no outstanding balance.")
                self._refresh()
                return

            dialog = DuePaymentDialog(self.view, invoice_id, customer_name, grand_total, paid_so_far, due_amount)
            if dialog.exec():
                amount = dialog.get_amount()
                new_id = InvoiceController.record_due_payment(invoice_id, amount)
                QMessageBox.information(
                    self.view, "Payment Recorded",
                    f"Payment of {cfg.CURRENCY_SYMBOL} {amount:,.2f} recorded against Invoice #{invoice_id} "
                    f"(record #{new_id})."
                )
                self._refresh()

                # Offer to save a PDF receipt for this specific due-payment right away
                file_path, _ = QFileDialog.getSaveFileName(
                    self.view, "Save Payment Receipt PDF", f"DuePayment_{new_id}.pdf", "PDF Files (*.pdf)"
                )
                if file_path:
                    if PDFGenerator.generate_invoice_pdf(new_id, file_path):
                        QMessageBox.information(self.view, "Success", "Payment receipt PDF saved successfully!")
                    else:
                        QMessageBox.critical(self.view, "Error", "Failed to compile the payment receipt PDF.")
        except ValueError as ve:
            QMessageBox.warning(self.view, "Invalid Payment", str(ve))
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Failed to record due payment: {e}")

    def handle_view_payment_history(self, invoice_id: int):
        """Shows the full chain (original invoice + every linked due-payment) for one invoice."""
        try:
            with get_db_session() as session:
                root = session.query(Invoice).filter_by(id=invoice_id, is_due_payment=False).first()
                if root:
                    customer_name = root.customer.name
                    chain = [{
                        "id": root.id,
                        "label": f"Invoice #{root.id} (Original Sale)",
                        "date": root.invoice_date.strftime("%Y-%m-%d"),
                        "amount": root.paid_amount,
                    }]
                    # Sort key stays on created_at (true timestamp) so same-day
                    # payments still order correctly -- invoice_date alone has
                    # no time-of-day to break ties with. The DISPLAYED date
                    # below still uses invoice_date, consistent with the rest
                    # of the app.
                    for dp in sorted(root.due_payments, key=lambda x: x.created_at):
                        chain.append({
                            "id": dp.id,
                            "label": f"Due Payment #{dp.id}",
                            "date": dp.invoice_date.strftime("%Y-%m-%d"),
                            "amount": dp.paid_amount,
                        })
                else:
                    customer_name = None

            if customer_name is None:
                QMessageBox.critical(self.view, "Error", f"Invoice #{invoice_id} not found.")
                return

            dialog = PaymentHistoryDialog(self.view, invoice_id, customer_name, chain)
            dialog.reprint_requested.connect(self._reprint_chain_record)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Could not load payment history: {e}")

    def _reprint_chain_record(self, record_id: int):
        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save PDF", f"Invoice_{record_id}.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            self.reprint_single_invoice(record_id, file_path)