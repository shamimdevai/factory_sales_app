"""
Customer Status (Silver/Golden/Platinum/...) computation engine.

NOTE ON NAMING: internally these are called "Tier" (CustomerTier model, this
module's name) to avoid confusion with Invoice.payment_status / effective_status
elsewhere in the codebase. Every UI-facing label for this concept must say
"Status" (column headers, badges, dialog titles) — see models.py CustomerTier
docstring.

Status is never stored on the Customer row — it's computed live, the same
philosophy as Invoice.effective_status:

  1. BASE STATUS (with HOLD): walk configured tiers from highest rank to
     lowest. For each tier, walk backward through that tier's own periods
     (calendar month or calendar year), starting at the current period, for
     up to `rank_hold_months` back. The most recent period whose total
     grand_total meets the tier's threshold becomes the "anchor" — the
     customer HOLDS that tier until rank_hold_months after that anchor
     period ends. Requalifying in a more recent period naturally resets the
     anchor (we always scan newest-first and take the first hit). No tier
     found within the hold window at any level -> "Standard".

  2. DECAY: independent of the hold mechanic above. If the customer has any
     outstanding due balance, find the oldest unpaid root invoice. Let
     age_days = days since that invoice's invoice_date (the actual purchase
     date, not the day it was entered into the system).
       - age_days <= grace_days                                -> no penalty
       - grace_days < age_days <= grace_days + decay_step_days  -> no penalty
         (rank stays the same through the 1st full decay step)
       - beyond that, 1 rank drops per additional fully-elapsed decay step,
         floored at "Standard" (can't go below the lowest tier / no tier).

  Final Status = base tier (with hold applied) minus decay downgrade steps.

DATE BASIS: every period/age calculation here is driven by Invoice.invoice_date
(the business/purchase date) rather than created_at (the true DB-insert
timestamp) — a backdated invoice counts toward the tier period and decay
clock of its REAL transaction date, not the day it happened to be entered.
"""
import calendar
from datetime import date, timedelta
from sqlalchemy import func
from src.database.models import Customer, Invoice, CustomerTier, AppSettings

STANDARD_LABEL = "Standard"


def _month_window(year: int, month: int, today: date):
    """Full calendar-month window [start_date, end_date], inclusive on both
    ends, end clipped to 'today' if this is the current (in-progress) month."""
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    natural_end = date(year, month, last_day)
    end_date = min(natural_end, today)
    return start_date, end_date


def _year_window(year: int, today: date):
    """Full calendar-year window [start_date, end_date], inclusive on both
    ends, end clipped to 'today' if this is the current (in-progress) year."""
    start_date = date(year, 1, 1)
    natural_end = date(year, 12, 31)
    end_date = min(natural_end, today)
    return start_date, end_date


def _sum_grand_total(customer_id: int, session, start_date: date, end_date: date) -> float:
    total = session.query(func.coalesce(func.sum(Invoice.grand_total), 0.0)).filter(
        Invoice.customer_id == customer_id,
        Invoice.is_due_payment == False,
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date,
    ).scalar()
    return total or 0.0


def _get_settings(session) -> AppSettings:
    settings = session.query(AppSettings).get(1)
    if not settings:
        # Defensive fallback — the migration seeds this row, but guard anyway
        # in case of a manually-wiped table.
        settings = AppSettings(id=1, grace_days=30, decay_step_days=30, rank_hold_months=6)
        session.add(settings)
        session.flush()
    return settings


def _find_held_anchor(customer_id: int, session, tier: CustomerTier, today: date, hold_months: int):
    """Walk backward through this tier's periods (current period first) looking
    for the most recent period that met the threshold. Returns that period's
    end date (the 'anchor') if found within the hold window, else None."""
    if tier.period == "yearly":
        max_offset = -(-hold_months // 12)  # ceil(hold_months / 12)
        for offset in range(0, max_offset + 1):
            year = today.year - offset
            start_date, end_date = _year_window(year, today)
            if _sum_grand_total(customer_id, session, start_date, end_date) >= tier.min_amount:
                return end_date
        return None
    else:  # "monthly"
        max_offset = hold_months
        for offset in range(0, max_offset + 1):
            month_index = (today.year * 12 + (today.month - 1)) - offset
            year, month = divmod(month_index, 12)
            month += 1
            start_date, end_date = _month_window(year, month, today)
            if _sum_grand_total(customer_id, session, start_date, end_date) >= tier.min_amount:
                return end_date
        return None


def _compute_base_tier(customer_id: int, session, today: date, hold_months: int):
    """Returns (tier, anchor_date) for the highest-rank CustomerTier this
    customer currently holds (earned now or within the hold window), or
    (None, None) for 'Standard'."""
    tiers_desc = session.query(CustomerTier).order_by(CustomerTier.rank.desc()).all()

    for tier in tiers_desc:
        anchor = _find_held_anchor(customer_id, session, tier, today, hold_months)
        if anchor is not None:
            return tier, anchor

    return None, None


def _oldest_unpaid_invoice_age_days(customer_id: int, session, today: date):
    """Days since the customer's longest-outstanding due balance's invoice_date
    (the real purchase date). Returns None if the customer has no root invoice
    with an outstanding effective_due_amount right now (i.e. fully paid up)."""
    root_invoices = session.query(Invoice).filter(
        Invoice.customer_id == customer_id,
        Invoice.is_due_payment == False,
    ).order_by(Invoice.invoice_date.asc(), Invoice.id.asc()).all()

    for inv in root_invoices:
        if inv.effective_due_amount > 0.001:
            return (today - inv.invoice_date).days

    return None


def evaluate_customer_status(customer_id: int, session, now: date = None) -> dict:
    """Main entry point. Returns a dict describing the customer's current
    Status, ready for direct display:

        {
            "base_tier": CustomerTier | None,
            "effective_tier": CustomerTier | None,
            "downgrade_steps": int,
            "held_since": date | None,   # anchor period-end that earned the base tier
            "oldest_unpaid_days": int | None,
            "display_name": str,       # e.g. "Golden" or "Standard" -- USE THIS IN UI
            "base_display_name": str,  # what it *would* be with no overdue penalty
        }

    `now` accepts a date (or datetime — .date() is applied automatically) for
    callers that want to evaluate as-of a specific day; defaults to today.
    """
    if now is None:
        today = date.today()
    elif hasattr(now, "date") and not isinstance(now, date):
        today = now.date()  # a datetime was passed — normalize to its date
    else:
        today = now

    settings = _get_settings(session)

    base_tier, held_since = _compute_base_tier(customer_id, session, today, settings.rank_hold_months)
    base_display_name = base_tier.name if base_tier else STANDARD_LABEL

    if base_tier is None:
        return {
            "base_tier": None,
            "effective_tier": None,
            "downgrade_steps": 0,
            "held_since": None,
            "oldest_unpaid_days": None,
            "display_name": STANDARD_LABEL,
            "base_display_name": STANDARD_LABEL,
        }

    oldest_unpaid_days = _oldest_unpaid_invoice_age_days(customer_id, session, today)

    downgrade_steps = 0
    if oldest_unpaid_days is not None:
        elapsed_after_grace = oldest_unpaid_days - settings.grace_days
        if elapsed_after_grace > 0:
            full_steps_elapsed = elapsed_after_grace // settings.decay_step_days
            downgrade_steps = max(0, int(full_steps_elapsed) - 1)

    effective_tier = base_tier
    if downgrade_steps > 0:
        # Walk tiers ascending by rank so we degrade by POSITION, not raw rank
        # arithmetic -- robust even if admin-edited ranks have gaps.
        tiers_asc = session.query(CustomerTier).order_by(CustomerTier.rank.asc()).all()
        base_index = next((i for i, t in enumerate(tiers_asc) if t.id == base_tier.id), None)
        if base_index is None:
            effective_tier = None
        else:
            effective_index = base_index - downgrade_steps
            effective_tier = tiers_asc[effective_index] if effective_index >= 0 else None

    return {
        "base_tier": base_tier,
        "effective_tier": effective_tier,
        "downgrade_steps": downgrade_steps,
        "held_since": held_since,
        "oldest_unpaid_days": oldest_unpaid_days,
        "display_name": effective_tier.name if effective_tier else STANDARD_LABEL,
        "base_display_name": base_display_name,
    }

def build_status_color_map(session, standard_color: str = "#95a5a6", palette: list = None):
    """Shared badge-color helper for any screen displaying Status. Returns
    (color_map, standard_color) where color_map is {tier.id: hex_color},
    assigned by RANK POSITION (highest tier first = palette[0]).

    UI callers should pass theme.STATUS_TIER_PALETTE and theme.STATUS_STANDARD_COLOR
    explicitly, so the actual color scheme lives in one editable place
    (theme.py) rather than here -- this module intentionally stays free of
    any theme.py/UI import so it remains pure business logic. The defaults
    below only exist as a safety net for callers that don't pass one."""
    tiers_desc = session.query(CustomerTier).order_by(CustomerTier.rank.desc()).all()
    palette = palette or ["#b8860b", "#95a5a6", "#cd7f32", "#1abc9c", "#3498db", "#9b59b6"]
    color_map = {}
    for i, t in enumerate(tiers_desc):
        color_map[t.id] = palette[i] if i < len(palette) else "#1ABC9C"
    return color_map, standard_color