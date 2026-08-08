import calendar
from datetime import datetime, date, time
from sqlalchemy import func
from src.database.connection import get_db_session
from src.database.models import Invoice, InvoiceItem, Customer
from src.views.dashboard_view import DashboardView
from src.utils.time_utils import to_local_str

class DashboardController:
    def __init__(self, view: DashboardView):
        self.view = view
        self.view.view_period_requested.connect(self.refresh_dashboard_data)

    @staticmethod
    def _resolve_period(period_filter: dict):
        """Turns a period filter dict into (start_dt, end_dt, label) covering full-day
        boundaries. start_dt/end_dt come back as None for 'all' (no date bound at all).
        Defaults to 'today' if no filter is given (e.g. on first app launch)."""
        period_filter = period_filter or {"mode": "today"}
        mode = period_filter.get("mode", "today")

        if mode == "today":
            today = date.today()
            return datetime.combine(today, time.min), datetime.combine(today, time.max), "Today"

        elif mode == "all":
            return None, None, "All Time"

        elif mode == "month":
            month = period_filter["month"]
            year = period_filter["year"]
            last_day = calendar.monthrange(year, month)[1]
            start_dt = datetime(year, month, 1, 0, 0, 0)
            end_dt = datetime(year, month, last_day, 23, 59, 59)
            label = f"{calendar.month_name[month]} {year}"
            return start_dt, end_dt, label

        elif mode == "year":
            year = period_filter["year"]
            start_dt = datetime(year, 1, 1, 0, 0, 0)
            end_dt = datetime(year, 12, 31, 23, 59, 59)
            return start_dt, end_dt, str(year)

        elif mode == "range":
            start_qdate = period_filter["start"]
            end_qdate = period_filter["end"]
            start_dt = datetime.combine(start_qdate.toPyDate(), time.min)
            end_dt = datetime.combine(end_qdate.toPyDate(), time.max)
            label = f"{start_qdate.toString('yyyy-MM-dd')} to {end_qdate.toString('yyyy-MM-dd')}"
            return start_dt, end_dt, label

        # Fallback — shouldn't normally be reached
        today = date.today()
        return datetime.combine(today, time.min), datetime.combine(today, time.max), "Today"

    def refresh_dashboard_data(self, period_filter: dict = None):
        """Queries database and feeds structured telemetry calculations to the View.
        `period_filter` scopes the 4 KPI cards to Today/All/Month/Year/Date Range; the
        'Recent 10 Records' feed below stays an unfiltered recent-activity list."""
        try:
            start_dt, end_dt, period_label = self._resolve_period(period_filter)
            has_date_bound = start_dt is not None  # False only for "All Time"

            with get_db_session() as session:
                # For "All Time", replace the plain label with the actual earliest/latest
                # invoice dates once we know them — needs a DB query, so it happens here
                # rather than in _resolve_period (which has no session access).
                if not has_date_bound:
                    first_dt, last_dt = session.query(
                        func.min(Invoice.created_at), func.max(Invoice.created_at)
                    ).filter(Invoice.is_due_payment == False).first()
                    if first_dt and last_dt:
                        first_date = to_local_str(first_dt).split(" ")[0]
                        last_date = to_local_str(last_dt).split(" ")[0]
                        period_label = f"All Time ({first_date} to {last_date})"
                    else:
                        period_label = "All Time (No records yet)"

                # 1. KPI tiles: EXCLUDE due-payment records, scoped to the selected period
                # (or unscoped entirely for "All Time").
                invoice_filters = [Invoice.is_due_payment == False]
                if has_date_bound:
                    invoice_filters.append(Invoice.created_at.between(start_dt, end_dt))

                invoices_stats = session.query(
                    func.count(Invoice.id).label("total_count"),
                    func.sum(Invoice.grand_total).label("total_revenue")
                ).filter(*invoice_filters).first()

                total_revenue = invoices_stats.total_revenue or 0.0
                total_invoices = invoices_stats.total_count or 0

                # 2. Itemized product volume splits — joined to Invoice so they respect
                # the same period + is_due_payment exclusion.
                item_filters_compost = [Invoice.is_due_payment == False, InvoiceItem.product_name.ilike("%compost%")]
                item_filters_worms = [Invoice.is_due_payment == False, InvoiceItem.product_name.ilike("%worm%")]
                if has_date_bound:
                    item_filters_compost.append(Invoice.created_at.between(start_dt, end_dt))
                    item_filters_worms.append(Invoice.created_at.between(start_dt, end_dt))

                compost_stats = session.query(func.sum(InvoiceItem.quantity)).join(Invoice).filter(
                    *item_filters_compost
                ).scalar() or 0.0
                worms_stats = session.query(func.sum(InvoiceItem.quantity)).join(Invoice).filter(
                    *item_filters_worms
                ).scalar() or 0.0

                self.view.update_metrics(total_revenue, compost_stats, worms_stats, total_invoices, period_label)

                # 3. Recent 10 Records — unfiltered by the period selector on purpose;
                # this is a "what just happened" feed, separate from the period summary
                # tiles above. Includes due-payment records, same as before.
                recent_records = session.query(Invoice).join(Customer).order_by(
                    Invoice.created_at.desc()
                ).limit(10).all()

                formatted_records = []
                for rec in recent_records:
                    if rec.is_due_payment:
                        formatted_records.append({
                            "id": rec.id,
                            "customer_name": f"{rec.customer.name}\n(Due Payment for #{rec.parent_invoice_id})",
                            "date": to_local_str(rec.created_at),
                            "items_count": 0,
                            "grand_total": None,
                            "status": "Payment Received",
                            "due": None,
                            "payment": rec.paid_amount,
                            "is_due_payment": True,
                        })
                    else:
                        formatted_records.append({
                            "id": rec.id,
                            "customer_name": rec.customer.name,
                            "date": to_local_str(rec.created_at),
                            "items_count": len(rec.items),
                            "grand_total": rec.grand_total,
                            "status": rec.effective_status,
                            "due": rec.effective_due_amount,
                            "payment": rec.paid_amount,
                            "is_due_payment": False,
                        })

                self.view.populate_recent_sales(formatted_records)

        except Exception as e:
            print(f"[Error loading Dashboard Data]: {e}")