from PyQt6.QtWidgets import QMessageBox
from src.database.connection import get_db_session
from src.database.models import Customer, CustomerType, CustomerTier
from src.views.customer_view import CustomerView, CustomerDialog
from src.utils.tier_engine import evaluate_customer_status, build_status_color_map
from src.utils.time_utils import to_local_str
from src.config import theme


class CustomerController:
    def __init__(self, view: CustomerView):
        self.view = view
        self.view.add_customer_requested.connect(self.add_customer)
        self.view.edit_customer_requested.connect(self.edit_customer)
        self.view.refresh_requested.connect(self.refresh_all)
        # NOTE: view.view_ledger_requested is intentionally NOT connected here --
        # it's wired directly in main_window.py to the History Ledger controller,
        # keeping cross-page navigation out of this controller (Rule 1).

        self.refresh_all()

    @staticmethod
    def _get_type_choices(session) -> list:
        types = session.query(CustomerType).order_by(CustomerType.name.asc()).all()
        return [{"id": t.id, "name": t.name} for t in types]

    def refresh_all(self):
        """Recomputes the full Directory + Pivot dataset in one pass. Called on
        page load and on explicit Refresh -- NEVER per-row/per-repaint, since
        Status evaluation runs several queries per customer (tier_engine)."""
        try:
            with get_db_session() as session:
                tier_colors, standard_color = build_status_color_map(
                    session, theme.STATUS_STANDARD_COLOR, theme.STATUS_TIER_PALETTE
                )
                customers = session.query(Customer).order_by(Customer.name.asc()).all()

                directory_rows = []
                pivot_rows = []
                totals = {
                    "invoices": 0, "discount": 0.0, "grand_total": 0.0,
                    "paid": 0.0, "due": 0.0, "compost_kg": 0.0, "worms_kg": 0.0,
                }

                for cust in customers:
                    status_info = evaluate_customer_status(cust.id, session)
                    tier = status_info["effective_tier"]
                    status_color = tier_colors.get(tier.id) if tier else standard_color

                    directory_rows.append({
                        "id": cust.id,
                        "name": cust.name,
                        "phone": cust.phone,
                        "email": cust.email,
                        "type_name": cust.customer_type.name if cust.customer_type else None,
                        "status_name": status_info["display_name"],
                        "status_color": status_color,
                    })

                    # Pivot aggregates -- ROOT SALE INVOICES ONLY (due-payment
                    # records excluded, consistent with Dashboard/History).
                    root_invoices = [inv for inv in cust.invoices if not inv.is_due_payment]
                    total_invoices = len(root_invoices)
                    total_discount = sum(inv.discount_amount for inv in root_invoices)
                    total_grand = sum(inv.grand_total for inv in root_invoices)
                    total_paid = sum(inv.effective_paid_amount for inv in root_invoices)
                    total_due = sum(inv.effective_due_amount for inv in root_invoices)
                    last_purchase_dt = max((inv.invoice_date for inv in root_invoices), default=None)
                    compost_kg = sum(
                        item.quantity for inv in root_invoices for item in inv.items
                        if "compost" in item.product_name.lower()
                    )
                    worms_kg = sum(
                        item.quantity for inv in root_invoices for item in inv.items
                        if "worm" in item.product_name.lower()
                    )

                    pivot_rows.append({
                        "id": cust.id,
                        "name": cust.name,
                        "invoices": total_invoices,
                        "discount": total_discount,
                        "grand_total": total_grand,
                        "paid": total_paid,
                        "due": total_due,
                        "last_purchase": last_purchase_dt.strftime("%Y-%m-%d") if last_purchase_dt else None,
                        "compost_kg": compost_kg,
                        "worms_kg": worms_kg,
                    })

                    totals["invoices"] += total_invoices
                    totals["discount"] += total_discount
                    totals["grand_total"] += total_grand
                    totals["paid"] += total_paid
                    totals["due"] += total_due
                    totals["compost_kg"] += compost_kg
                    totals["worms_kg"] += worms_kg

            self.view.populate_directory(directory_rows)
            self.view.populate_pivot(pivot_rows, totals)

        except Exception as e:
            print(f"[Error loading Customer Data]: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to load customer data:\n{e}")

    def add_customer(self):
        with get_db_session() as session:
            type_choices = self._get_type_choices(session)

        dialog = CustomerDialog(self.view, type_choices=type_choices)
        if not dialog.exec():
            return

        data = dialog.get_data()
        try:
            with get_db_session() as session:
                existing = session.query(Customer).filter(Customer.phone == data["phone"]).first()
                existing_name = existing.name if existing else None

            if existing_name:
                QMessageBox.warning(
                    self.view, "Duplicate Phone",
                    f"A customer with phone '{data['phone']}' already exists ({existing_name})."
                )
                return

            with get_db_session() as session:
                session.add(Customer(
                    name=data["name"], phone=data["phone"], email=data["email"] or None,
                    address=data["address"] or None, customer_type_id=data["customer_type_id"]
                ))
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Failed to add customer: {e}")

    def edit_customer(self, customer_id: int):
        with get_db_session() as session:
            customer = session.query(Customer).get(customer_id)
            if customer:
                type_choices = self._get_type_choices(session)
                name, phone, email = customer.name, customer.phone, customer.email or ""
                address, type_id = customer.address or "", customer.customer_type_id
            else:
                type_choices = None

        if type_choices is None:
            QMessageBox.critical(self.view, "Error", f"Customer #{customer_id} not found.")
            return

        dialog = CustomerDialog(
            self.view, type_choices=type_choices, name=name, phone=phone,
            email=email, address=address, current_type_id=type_id
        )
        if not dialog.exec():
            return

        data = dialog.get_data()
        try:
            with get_db_session() as session:
                dup = session.query(Customer).filter(
                    Customer.phone == data["phone"], Customer.id != customer_id
                ).first()
                dup_name = dup.name if dup else None

            if dup_name:
                QMessageBox.warning(
                    self.view, "Duplicate Phone",
                    f"A customer with phone '{data['phone']}' already exists ({dup_name})."
                )
                return

            with get_db_session() as session:
                customer = session.query(Customer).get(customer_id)
                if not customer:
                    return
                customer.name = data["name"]
                customer.phone = data["phone"]
                customer.email = data["email"] or None
                customer.address = data["address"] or None
                customer.customer_type_id = data["customer_type_id"]
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Failed to update customer: {e}")