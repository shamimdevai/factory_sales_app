from PyQt6.QtWidgets import QMessageBox
from src.database.connection import get_db_session
from src.database.models import CustomerTier, CustomerType, AppSettings
from src.views.settings_view import SettingsView, TierDialog, TypeDialog


class SettingsController:
    def __init__(self, view: SettingsView):
        self.view = view

        self.view.add_tier_requested.connect(self.add_tier)
        self.view.edit_tier_requested.connect(self.edit_tier)
        self.view.delete_tier_requested.connect(self.delete_tier)
        self.view.move_tier_up_requested.connect(lambda tid: self.move_tier(tid, direction=-1))
        self.view.move_tier_down_requested.connect(lambda tid: self.move_tier(tid, direction=1))

        self.view.add_type_requested.connect(self.add_type)
        self.view.edit_type_requested.connect(self.edit_type)
        self.view.delete_type_requested.connect(self.delete_type)

        self.view.save_rules_requested.connect(self.save_rules)

        self.refresh_all()

    def refresh_all(self):
        self._refresh_tiers()
        self._refresh_types()
        self._refresh_rules()

    # ---------------- Status Tiers ----------------
    def _refresh_tiers(self):
        with get_db_session() as session:
            tiers = session.query(CustomerTier).order_by(CustomerTier.rank.desc()).all()
            data = [
                {"id": t.id, "name": t.name, "min_amount": t.min_amount, "period": t.period}
                for t in tiers
            ]
        self.view.populate_tiers(data)

    def add_tier(self):
        dialog = TierDialog(self.view)
        if dialog.exec():
            data = dialog.get_data()
            with get_db_session() as session:
                max_rank = session.query(CustomerTier).order_by(CustomerTier.rank.desc()).first()
                next_rank = (max_rank.rank + 1) if max_rank else 1
                session.add(CustomerTier(
                    name=data["name"], min_amount=data["min_amount"],
                    period=data["period"], rank=next_rank
                ))
            self._refresh_tiers()

    def edit_tier(self, tier_id: int):
        with get_db_session() as session:
            tier = session.query(CustomerTier).get(tier_id)
            if not tier:
                return
            dialog = TierDialog(self.view, name=tier.name, min_amount=tier.min_amount, period=tier.period)
            if dialog.exec():
                data = dialog.get_data()
                tier.name = data["name"]
                tier.min_amount = data["min_amount"]
                tier.period = data["period"]
        self._refresh_tiers()

    def delete_tier(self, tier_id: int):
        with get_db_session() as session:
            tier = session.query(CustomerTier).get(tier_id)
            if not tier:
                return
            confirm = QMessageBox.question(
                self.view, "Delete Status Tier",
                f"Delete the '{tier.name}' Status tier? Customers currently holding this "
                f"Status will re-evaluate to whatever tier they now qualify for.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                session.delete(tier)
        self._refresh_tiers()

    def move_tier(self, tier_id: int, direction: int):
        """direction: -1 = move up (toward higher rank/priority), +1 = move down."""
        with get_db_session() as session:
            tiers_asc = session.query(CustomerTier).order_by(CustomerTier.rank.asc()).all()
            index = next((i for i, t in enumerate(tiers_asc) if t.id == tier_id), None)
            if index is None:
                return
            swap_index = index - direction  # moving up in rank = swapping with the next-higher-rank neighbor
            if not (0 <= swap_index < len(tiers_asc)):
                return

            tier_a = tiers_asc[index]
            tier_b = tiers_asc[swap_index]
            rank_a, rank_b = tier_a.rank, tier_b.rank

            # Swap via a temporary sentinel value to avoid violating the
            # UNIQUE(rank) constraint mid-transaction.
            tier_a.rank = -1
            session.flush()
            tier_b.rank = rank_a
            session.flush()
            tier_a.rank = rank_b
        self._refresh_tiers()

    # ---------------- Customer Types ----------------
    def _refresh_types(self):
        with get_db_session() as session:
            types = session.query(CustomerType).order_by(CustomerType.name.asc()).all()
            data = [{"id": t.id, "name": t.name} for t in types]
        self.view.populate_types(data)

    def add_type(self):
        dialog = TypeDialog(self.view)
        if dialog.exec():
            name = dialog.get_name()
            with get_db_session() as session:
                exists = session.query(CustomerType).filter(CustomerType.name.ilike(name)).first()
                if exists:
                    QMessageBox.warning(self.view, "Duplicate Type", f"'{name}' already exists.")
                    return
                session.add(CustomerType(name=name))
            self._refresh_types()

    def edit_type(self, type_id: int):
        with get_db_session() as session:
            ctype = session.query(CustomerType).get(type_id)
            if not ctype:
                return
            dialog = TypeDialog(self.view, name=ctype.name)
            if dialog.exec():
                new_name = dialog.get_name()
                dup = session.query(CustomerType).filter(
                    CustomerType.name.ilike(new_name), CustomerType.id != type_id
                ).first()
                if dup:
                    QMessageBox.warning(self.view, "Duplicate Type", f"'{new_name}' already exists.")
                    return
                ctype.name = new_name
        self._refresh_types()

    def delete_type(self, type_id: int):
        with get_db_session() as session:
            ctype = session.query(CustomerType).get(type_id)
            if not ctype:
                return
            confirm = QMessageBox.question(
                self.view, "Delete Customer Type",
                f"Delete the '{ctype.name}' type? Customers with this type will have it cleared.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                session.delete(ctype)
        self._refresh_types()

    # ---------------- Status Rules ----------------
    def _refresh_rules(self):
        with get_db_session() as session:
            settings = session.query(AppSettings).get(1)
            if not settings:
                settings = AppSettings(id=1, grace_days=30, decay_step_days=30, rank_hold_months=6)
                session.add(settings)
                session.flush()
            grace, decay, hold = settings.grace_days, settings.decay_step_days, settings.rank_hold_months
        self.view.populate_rules(grace, decay, hold)

    def save_rules(self, grace_days: int, decay_step_days: int, rank_hold_months: int):
        with get_db_session() as session:
            settings = session.query(AppSettings).get(1)
            if not settings:
                settings = AppSettings(id=1)
                session.add(settings)
            settings.grace_days = grace_days
            settings.decay_step_days = decay_step_days
            settings.rank_hold_months = rank_hold_months
        QMessageBox.information(self.view, "Saved", "Status rules updated.")