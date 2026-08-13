# Vermi-Composting Factory Invoice & Sales App (Project Specification & State)

> **Last updated:** 2026-08-11 — reflects the actual current, working state of the codebase, including the new Customer Management / Status (tier) system, Settings page, and an app-wide responsive-UI pass. Start new chats by uploading this file plus the current project zip (or the specific files you're working on).

---

## 📌 Project Overview
A professional Windows desktop application for a vermi-composting factory (branded **Chashi-Bondhu**), selling **Vermi-compost** and **Earthworms**. Replaces manual Excel invoicing with a PyQt6 desktop app backed by PostgreSQL, with PDF/Excel export and digital signatures. It provides a secure UI for entering transaction data, tracks database records, computes dashboard statistics, and now includes full customer relationship management (customer directory, purchase-history pivot, and a purchase-volume-based Status/loyalty-tier system).

---

## 🛠️ Tech Stack
- **OS Platform:** Windows 10/11 (target deployment)
- **Language:** Python 3.11
- **UI Framework:** PyQt6 (`Fusion` style + explicit light `QPalette`, centrally themed via `src/config/theme.py`)
- **Database:** PostgreSQL + SQLAlchemy ORM
- **Migrations:** Alembic (currently at 7 revisions — see below)
- **Exports:** ReportLab (PDF), openpyxl (Excel)
- **Compiler:** PyInstaller (.exe bundling)
- **Env management:** python-dotenv (for local credential isolation)

---

## ⚠️ Correction vs. earlier project-state versions
An earlier version of this document incorrectly stated that invoices used a free-text `customer_name` field with no dedicated `Customer` model. That was wrong — the actual codebase has had a `Customer` model and a **required** (`nullable=False`) `Invoice.customer_id` FK since the **initial migration** (`8f6a5632b5e4`). What genuinely didn't exist before this session: `CustomerType`, `CustomerTier` (Status), `AppSettings`, any Customers/Settings UI pages, a searchable customer picker on the Invoice Terminal, or any of the responsive-UI theming infrastructure. All of that is new, documented below.

---

## ✅ Current Feature State (verified working)

### Dashboard (`dashboard_view.py` + `dashboard_controller.py`)
- KPI tiles (Total Revenue, Compost kg, Worms kg, Total Invoices).
- **Period selector** (Row 1, light-blue tinted `QFrame`): dropdown **View:** `Today` (default) / `Month` (month name + year) / `Year` / `Date Range` (From/To) / `All`, plus a **🔍 View** button. Only the input(s) relevant to the selected mode are visible. KPI tiles are recalculated and scoped to whichever period is selected; excludes due-payment records from the count/revenue math (see Due-Payment Chain section).
  - **"All"** mode shows a caption like `Showing: All Time (2026-07-18 to 2026-07-20)` — the actual earliest/latest invoice dates are queried live, excluding due-payment records. Falls back to `All Time (No records yet)` if there are no invoices at all.
- KPI cards (Row 2) show a small **"Showing: ..."** caption confirming the active period.
- **"Recent 10 Records"** table (8 columns) is a global, **unfiltered** recent-activity feed, separate from the period selector. Includes due-payment records inline.
- Table columns are data-responsive: short/uniform columns use `ResizeToContents`; Customer Name/Status stay `Interactive` with word-wrap.
- Compost/Worms kg aggregation matches product names by keyword, joined to `Invoice` so period scoping and due-payment exclusion apply correctly.
- **Not yet migrated** to the new `theme.configure_responsive_table()` helper (see "Responsive UI" section) — still uses hand-set column widths. Left as-is intentionally; only Customers/Settings were converted this round, pending confirmation before rolling out further.

### Invoice Terminal (`invoice_view.py` + `invoice_controller.py`)
Financial fields, in calculation order:
```
taxable_amount = subtotal − discount
VAT_amount     = taxable_amount × VAT_rate
grand_total    = taxable_amount + VAT_amount + transport_charge − less_adjustment   (clamped ≥ 0)
due_amount     = grand_total − paid_amount                        (computed property, not stored)
```
- **Discount**: flat amount, user-entered per invoice, applied before VAT.
- **VAT**: user-entered percentage per invoice, default **0%**.
- **Transport**: optional flat add-on via checkbox (`chk_transport`), applied after VAT, before Less Adjustment. Only affects `grand_total` and only shows as a PDF line if checked at issuing time (`show_transport_charge` flag, immutable after issuing).
- **Less Adjustment**: flat manual deduction applied after VAT/Transport, before grand total.
- **Payment Status** dropdown: `Paid`, `Due`, `Partial Payment` — same paid/due math as before.
- Status text and paid/due amounts color-coded via `company_config.resolve_status_color()`.
- Metrics box uses `QGridLayout` (fixed-shape). Cart items table uses fixed column widths with native scrollbars.

**Customer Details box — rebuilt this session (was 4 plain text fields, now):**
- **Searchable combo** (`combo_customer`, editable `QComboBox`) with its built-in `QCompleter` tuned to `MatchContains` + case-insensitive, so typing any substring of a customer's **name or phone** filters live. Placeholder text `"Search Customer by Name or Phone"` doubles as the field's label — no separate `QLabel` above it (removed; was causing a large blank-space rendering bug, see Known Bugs Fixed).
- Selecting a real customer shows a read-only info line: `Phone: ... | Type: ... | Status: ...`, sourced entirely from data already loaded into the combo's `itemData` (no extra DB round-trip on selection).
- **"+ New"** button reveals an inline "New Customer" panel (Name*/Phone*/Email/Address/Type dropdown + Add Customer/Cancel) directly in the Invoice page — no dialog/context switch. Submitting registers the customer immediately and auto-selects them back in the combo (`select_customer_by_id`).
- `InvoiceController.refresh_customer_list()` loads all customers (each with live-computed Status via `tier_engine`) plus Customer Type choices; called on controller construction **and** every time `main_window.py` switches back to the Invoice page, so customers added elsewhere (Customers/Settings pages) appear without an app restart.
- **Removed:** the old get-or-create-by-phone logic that silently **overwrote** an existing customer's name/email/address if the operator typed it slightly differently on a repeat sale. Customer selection is now always explicit (pick from the list or use "+ New") — see Known Bugs Fixed.
- Card is pinned to its natural top-aligned height (`QSizePolicy.Fixed` vertically + `AlignTop` + `left_panel.addStretch()`) so it can't be stretched tall by the taller "Cart Items" card in the same row (see Responsive UI section).
- "Issue Invoice" now emits `{"customer_id": ..., ...}` instead of raw name/phone/email/address strings; `commit_invoice` fetches the selected `Customer` by id and errors cleanly if somehow not found, rather than ever creating/overwriting one at issue time.

### Due-Payment Chain (`models.py`, `invoice_controller.py`, `history_view.py`/`history_controller.py`, `due_payment_dialog.py`, `pdf_generator.py`)
Unchanged this session. Once issued, an invoice is **immutable**. `Due`/`Partial Payment` invoices track later payments as linked `is_due_payment=True` rows (`parent_invoice_id` always points to the root). Computed properties `effective_paid_amount` / `effective_due_amount` / `effective_status` remain the source of truth everywhere a balance/status is shown — including the new Customer Purchase Summary pivot (see below).

### 🆕 Customer Management (`customer_view.py` + `customer_controller.py`)
New sidebar page, two tabs:

**Tab 1 — Customer Directory**
- Table: Name, Phone, Email, Type, **Status** (color-coded badge — see "Status/Tier system" below), Actions (✏️ Edit / 🧾 View Ledger).
- **"+ Add Customer"** opens `CustomerDialog` (Name*/Phone*/Email/Address/Type). Duplicate-phone checked both client-side (friendly warning) and by the DB's `UNIQUE` constraint.
- Client-side **Search** box (name/phone) filters row visibility instantly — no re-query.

**Tab 2 — Purchase Summary (pivot)**
- Columns: Total Invoices (root sale invoices only), Total Grand Total, **Total Discount**, Total Paid (`effective_paid_amount`), Total Due (`effective_due_amount`), Last Purchase Date, Compost (kg), Worms (kg), Actions (🧾 View Ledger).
- **Frozen TOTAL footer**: a *separate* 1-row `QTableWidget` pinned directly below the scrollable main table (`table_pivot_totals`) — always visible regardless of scroll position, styled via `theme.totals_row_style()` (pale blue-gray band + accent top border). Its columns are kept glued to the main table via `sectionResized` + horizontal-scrollbar sync signals, rather than being independently responsive, to avoid any rounding drift between two separately-stretched headers.
- 🧾 **View Ledger** (either tab) emits `view_ledger_requested(customer_id, customer_name)`, wired in `main_window.py` to switch to the History Ledger page pre-filtered to that customer (see History Ledger section).
- `CustomerController.refresh_all()` computes **both tabs in one pass**, once per page load/Refresh click — deliberately **never** per-row/per-repaint, since Status evaluation runs several queries per customer via `tier_engine`.
- Page-level `QLineEdit` search filters row visibility on both tabs client-side.
- Header buttons (🔄 Refresh / + Add Customer) are **responsive** — see "Responsive UI" section.

### 🆕 Status / Tier System (`src/utils/tier_engine.py`)
Customer "Status" (Silver/Golden/Platinum/... — names fully admin-defined) is **never stored** on the `Customer` row; it's computed live, same philosophy as `Invoice.effective_status`.

> **Naming note:** internally called "Tier" (`CustomerTier` model, `tier_engine.py`) to avoid confusion with `Invoice.payment_status`/`effective_status`. Every **UI-facing** label must say **"Status"** (column headers, badges, dialog titles) — this is intentional and documented in `models.py`'s `CustomerTier` docstring and `tier_engine.py`'s module docstring. Don't rename the underlying model/module.

**Computation logic (`evaluate_customer_status(customer_id, session, now=None)`):**

1. **Base Status (with HOLD):** walk configured tiers from highest rank to lowest. For each tier, walk backward through that tier's own periods (calendar month or calendar year, per-tier configurable), starting at the current period, up to `rank_hold_months` back. The **most recent period** whose total `grand_total` (root sale invoices only) meets the tier's threshold becomes the "anchor" — the customer **holds** that tier until `rank_hold_months` after the anchor period ends. Requalifying in a more recent period naturally resets the anchor (scan is newest-first, first hit wins). No tier found within the hold window → **"Standard"**.
2. **Decay (independent of hold):** if the customer has any outstanding due balance, find the oldest unpaid root invoice. Let `age_days` = days since that invoice was created.
   - `age_days ≤ grace_days` → no penalty.
   - `grace_days < age_days ≤ grace_days + decay_step_days` → still no penalty (rank stays through the 1st full decay step).
   - Beyond that: **1 rank drops per additional fully-elapsed decay step**, floored at "Standard". Degrades by **list position** among tiers sorted by rank (not raw rank-number subtraction) — robust even if an admin later deletes a tier or leaves rank gaps.
3. **Final Status** = base tier (with hold applied) minus decay downgrade steps.

- **Worked example:** customer hits Platinum in January (monthly period) → held through June even with low/no purchases (`rank_hold_months=6` default). If they requalify at Platinum-level again in June, June becomes the new anchor (checked before January is ever reached in the backward scan).
- `build_status_color_map(session, standard_color, palette)` — shared badge-color helper (assigns colors by **rank position**, not tier name; highest tier → `palette[0]`). Callers **must** pass `theme.STATUS_TIER_PALETTE` / `theme.STATUS_STANDARD_COLOR` explicitly (see Responsive UI / Central Theme section) — this module has zero UI/theme imports by design, staying pure business logic.
- **Performance note:** `_compute_base_tier` runs multiple queries per tier per customer (bounded by `rank_hold_months`). Fine for a Directory/Pivot page refresh at factory scale; must **never** be called per-row/per-repaint — only once per page load/Refresh, which is how both `CustomerController` and `InvoiceController` use it.

### 🆕 Settings Page (`settings_view.py` + `settings_controller.py`)
New sidebar page, three sections:

1. **Customer Status Tiers** — table (Status Name, Min. Amount, Period, Reorder ▲▼, Actions). Add/Edit via `TierDialog` (Name, Min. Purchase Amount, Monthly/Yearly). Reordering swaps `rank` values using a **temporary sentinel value** (`-1`) mid-transaction to avoid tripping the DB's `UNIQUE(rank)` constraint. Deleting a tier is safe — `tier_engine` re-evaluates any affected customer to whatever they now qualify for.
2. **Customer Types** — simple Add/Edit/Delete list (`TypeDialog`, name-only, duplicate-checked case-insensitively). Deleting a type in use `SET NULL`s it on affected customers (DB-level `ondelete="SET NULL"`).
3. **Status Rules** — three `QSpinBox` fields: **Grace Period** (days), **Decay Step** (days), **Status Hold Period** (months) — read/write the single `AppSettings` row (`id=1`).
- Header "+ Add" buttons are **responsive** — see below.

### Sales History Ledger (`history_view.py` / `history_controller.py`)
**Filter bar redesigned this session** — now exactly **3 modes** (was 4):
- **"Quick Search"** *(new default)* — one live/auto text box (debounced ~300ms via `QTimer`), matching **Invoice ID, Customer Name, Phone, Date, effective Status, Grand Total, and effective Due** all at once. Empty box = show all records. Replaces the old separate "Invoice ID" / "Customer Name" modes (functionality folded in). No Search button needed/shown for this mode.
- **"Date Range"** — unchanged (From/To date pickers + explicit 🔍 Search button).
- **"Status"** — unchanged (dropdown + explicit Search button); still filtered in Python since `effective_status` is a computed property.
- **"✖ Clear Search"** button — always visible; resets to Quick Search mode with an empty box (shows all) and clears any active customer-ledger filter.
- **Export** consolidated into a **single "⬇ Export" button with a click-menu** (`QToolButton` + `QMenu`), offering "Export to PDF" / "Export to Excel" — replaces the old two separate buttons; easy to extend with more formats later.
- **`customer_id` filter mode** *(new, programmatic-only — not in the dropdown)*: `apply_customer_filter(customer_id, customer_name)` shows a dismissible banner ("Showing ledger for: X — ✖ Clear Filter") and overrides whatever the dropdown is set to, until cleared or a manual mode is picked. This is how the Customers page's "View Ledger" action works — `HistoryController.show_customer_ledger()` is the entry point, called from `main_window._go_to_customer_ledger()`.
- Table: Invoice ID, Customer, Date, Discount, Grand Total, Status (color-coded, effective), Due (effective), Actions (📄/💰/🧾).
- Excel/PDF export both reuse whatever filter is currently active via `_get_filtered_records()`.
- **Fixed a bug** where the Search button incorrectly stayed visible on first page load in Quick Search mode (the visibility-sync method was only ever triggered by the dropdown's `currentTextChanged` signal, which never fires just from constructing the widgets — now explicitly called once after setup).
- **Not yet migrated** to `theme.configure_responsive_table()` (still fixed/interactive column widths) — same "pending confirmation before wider rollout" status as Dashboard.

### Database (`models.py`)
`Invoice` fields: `customer_id` (FK, `nullable=False`), `total_amount` (subtotal), `discount_amount`, `tax_rate` (VAT), `less_adjustment`, `transport_charge`, `show_transport_charge`, `grand_total`, `paid_amount`, `payment_status`, `parent_invoice_id`, `is_due_payment`, `created_at` (naive UTC), plus computed properties `due_amount`, `effective_paid_amount`, `effective_due_amount`, `effective_status`.

**🆕 New models this session:**
- `Customer` — gained `customer_type_id` (FK → `customer_types`, nullable, `ON DELETE SET NULL`). Existing fields (`name`, `phone` unique, `email`, `address`, `created_at`) unchanged.
- `CustomerType` — `id`, `name` (unique). Admin-managed via Settings.
- `CustomerTier` — `id`, `name`, `min_amount`, `period` (`"monthly"`/`"yearly"`), `rank` (unique). Admin-managed via Settings. **UI label = "Status"**, see naming note above.
- `AppSettings` — singleton row (`id=1`): `grace_days`, `decay_step_days`, `rank_hold_months`.

**Migrations (run `alembic upgrade head` — `init_db()` alone won't add columns to an existing table):**
1. `8f6a5632b5e4` — initial schema (includes `Customer` + required `Invoice.customer_id` from day one)
2. `c4d8f2a91b6e` — adds `discount_amount`, `paid_amount`
3. `d7f3a2c8b915` — adds `less_adjustment`
4. `e2a9c1f74d38` — adds `parent_invoice_id`, `is_due_payment` (due-payment chain)
5. `f7c3d81a2e56` — adds `transport_charge`, `show_transport_charge`
6. `a1b2c3d4e5f6` — adds `customer_types`, `customer_tiers`, `app_settings` tables + `customers.customer_type_id`; **seeds default data**: Customer Types (Retail, Wholesale, Distributor, Farmer) and Status tiers (Silver 10,000/mo rank 1, Golden 50,000/mo rank 2, Platinum 100,000/mo rank 3) — all admin-editable afterward, never re-seeded
7. `g2h3i4j5k6l7` — adds `app_settings.rank_hold_months` (default 6)

### PDF Invoice Engine (`pdf_generator.py`)
Unchanged this session. Header logo, two layouts dispatched by `is_due_payment` (`_build_sale_invoice_pdf` / `_build_due_payment_pdf`), Bengali `৳` glyph fix (inline `<font>` wrap only), dynamic `num_summary_rows` for the optional Transportation row, fixed footer, theme-driven section backgrounds via `src/config/pdf_styles.py`.

### Timezone fix (`src/utils/time_utils.py`)
Unchanged. `to_local_str(dt)` (fixed +6h offset) used everywhere a timestamp is shown, including the new Purchase Summary's "Last Purchase" column and `tier_engine`'s age calculations (naive UTC `datetime.utcnow()`, matching `created_at`'s storage convention).

### White-labeling (`src/config/company_config.py`)
Unchanged. Client branding only — name, address, contact info, currency symbol, logo/icon paths, `STATUS_COLORS`/`resolve_status_color()` (for **invoice payment status** — Paid/Due/Partial — do not confuse with the new **Customer Status/tier** badge colors, which live separately in `theme.py`, see below).

---

## 🎨 Central UI Theme — `src/config/theme.py`
Expanded significantly this session. This file is now the **single source of truth** for both static style strings *and* responsive layout behavior/helpers — the explicit design direction going forward: any new page should call into `theme.py` rather than hand-rolling table/column/button setup.

**Existing (unchanged):** `PAGE_BACKGROUND`, `SIDEBAR_BACKGROUND`, `SIDEBAR_HOVER`, `CARD_BACKGROUND`, `BORDER_COLOR`, `ACCENT`/`ACCENT_DARK`, `TEXT_PRIMARY`, `TEXT_MUTED`; `card_frame_style()`, `input_style()` (auto-appends `combobox_dropdown_style()` for any `"QComboBox"` selector), `combobox_dropdown_style()`.

**🆕 New this session:**
- `TOTALS_ROW_BACKGROUND` + `totals_row_style()` — frozen/footer summary-row styling (pale blue-gray band, accent top border). Used by Customer Purchase Summary's `table_pivot_totals`; intended for any future pinned-summary-row table.
- `STATUS_TIER_PALETTE` + `STATUS_STANDARD_COLOR` — **single source of truth for Customer Status badge colors**, assigned by **rank position** (highest tier = `palette[0]`), not tier name. Consumed by both `customer_controller.py` (Directory/Pivot badges) and `invoice_controller.py` (customer-picker Status line) via `tier_engine.build_status_color_map(session, standard_color, palette)` — previously these lived as two independently-duplicated palettes in the two controllers; now consolidated. **To change Status colors app-wide, edit only this one list.**
- `TABLE_MIN_SECTION_SIZE` (60px) + `configure_responsive_table(table, columns, min_section_size=...)` — the central responsive-table helper. `columns` is an ordered list of `(width_px, "stretch"|"fixed")` tuples. Sets baseline pixel widths **first**, then applies `QHeaderView.ResizeMode.Stretch`/`Fixed` **second** — Qt's Stretch mode preserves relative proportions between stretch columns using their size at the moment Stretch is applied, so this call order is what makes proportional (not equal-split) responsiveness work. Also hides the default row-number vertical header. **⚠️ Call-order requirement (caused a real bug once): must be called BEFORE `setHorizontalHeaderLabels()`** — a table still has 0 columns until this runs, and Qt silently discards header-label text set against a column that doesn't exist yet.
- `SIDEBAR_WIDTH` (240) + `SIDEBAR_LOGO_WIDTH_RATIO` (0.55) + `sidebar_logo_size()` — sidebar panel width and logo size are now a single proportional relationship. Change `SIDEBAR_WIDTH` alone and the logo auto-scales to match; change `SIDEBAR_LOGO_WIDTH_RATIO` alone to resize the logo relative to a fixed panel width. `SIDEBAR_BRAND_FONT_SIZE` (16) — brand label font, fixed (see Known Bugs Fixed re: dynamic shrinking being removed).
- `SIDEBAR_COMPACT_HEIGHT_BREAKPOINT` / `SIDEBAR_LOGO_SIZE_COMPACT` / `SIDEBAR_BRAND_FONT_COMPACT` — **defined but currently unused/dead** (the dynamic-shrink-on-resize behavior they powered was removed — see Known Bugs Fixed). Left in place harmlessly in case a genuine small-screen compact mode is wanted later.
- `HEADER_BUTTON_COMPACT_BREAKPOINT` (650) + `install_responsive_buttons(container, button_specs, breakpoint_width=...)` — installs a `QObject` event filter (`_ResponsiveButtonFilter`) on a container widget that watches its resize events and swaps each registered button between full text and compact/icon-only text once the container's width crosses the breakpoint. Compact-mode buttons get their full label set as a **tooltip** (only while compacted — cleared when full text is showing) so the button's function is still discoverable on hover. Currently wired up on: Customers page header (Refresh/Add Customer) and Settings page (Add Status Tier/Add Type).

**Applied so far:** Customers page (Directory table, Pivot table + frozen totals footer, header buttons), Settings page (Tiers table, Types table, header buttons), sidebar (width/logo ratio, scroll-wrapped). **Not yet applied:** Dashboard, Invoice Terminal (cart/item tables), History Ledger table — intentionally deferred pending your confirmation the style is right, per your own instruction to prove it out first before wider rollout.

---

## 📱 Responsive UI — what was actually broken and fixed this session
This was a multi-round debugging effort; documenting the real root causes so they aren't reintroduced.

1. **Fixed-pixel table columns never responded to window resize** — every table used `ResizeMode.Interactive` with hardcoded pixel widths; shrinking the window just triggered horizontal scrolling even when columns could have compressed to fit. **Fixed** via `theme.configure_responsive_table()` (see above) on Customers/Settings tables.
2. **Sidebar overlap/ghosting bug at small window sizes** — root cause: the sidebar `QFrame` had no scroll area, and the window's allowed minimum size (25% of screen, floored at 480×400 via `_apply_dynamic_minimum_size()`) could go smaller than the sidebar's true required content height (logo + brand + 6 nav buttons + footer). With nowhere to put the overflow, Qt drew widgets overlapping instead of erroring. **An initial attempted fix** (shrink logo/font dynamically past a height breakpoint) only moved the breakpoint and didn't solve the root cause — plus it had the side effect of shrinking the logo even at *normal* window sizes below the breakpoint. **Real fix:** wrapped the sidebar in its own `QScrollArea` (`sidebar_scroll`, fixed width = `theme.SIDEBAR_WIDTH`, `widgetResizable(True)`, vertical-scroll-as-needed, horizontal-never) — exactly the same technique already used for every page's content via `_wrap_scrollable()`. The dynamic logo/font-shrinking code was **removed entirely** afterward as unnecessary once the scroll area made it a non-issue; logo/brand are now always full, fixed size (`theme.sidebar_logo_size()` / `theme.SIDEBAR_BRAND_FONT_SIZE`).
3. **Logo/brand not horizontally centered** — `setAlignment(AlignCenter)` alone wasn't reliable inside the new scroll-wrapped sidebar layout. **Fixed** by wrapping each in its own stretch-padded `QHBoxLayout` (`addStretch()` / widget / `addStretch()`), which guarantees centering regardless of the widget's own sizeHint or scrollbar-driven width quirks.
4. **Customer Details card (Invoice Terminal) rendering as a large blank box** — root cause: `left_panel` (containing the Customer Details + Add Products cards, stacked vertically) had no `addStretch()` at the end, so leftover vertical space (from the taller "Cart Items" card in the parallel right column) bled into the Customer Details `QFrame`, pushing its actual content down and leaving a gap under the title. **Fixed:** `frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)` + `layout.setAlignment(Qt.AlignTop)` on the card itself, plus `left_panel.addStretch()` at the end of the column so leftover height goes there instead.
5. **Table header labels silently disappearing (showing "1, 2, 3..." instead)** — caused by calling `setHorizontalHeaderLabels()` **before** `theme.configure_responsive_table()` on a freshly-constructed (0-column) `QTableWidget`; Qt discards labels set against columns that don't exist yet. **Fixed** by reordering: `configure_responsive_table()` first (sets column count), `setHorizontalHeaderLabels()` second. Documented as a call-order requirement directly in the helper's docstring to prevent recurrence.
6. **Header buttons ("+ Add Customer" etc.) appearing to not respond to shrinking, even with visible space** — root cause: `CustomerView`/`SettingsView` had `self.setMinimumWidth(950)` / `700` set, forcing the *entire page* to never shrink below that, so the whole page content just horizontal-scrolled as one block — the compact-button logic was technically working but scrolled out of view. **Fixed** by removing those page-level minimum-width calls entirely, letting `install_responsive_buttons()` actually do its job against the page's real available width.
7. **Compact (icon-only) buttons had no way to see their function** — **Fixed** by having `install_responsive_buttons()` set the full label text as a tooltip whenever a button is in compact mode (cleared when showing full text).
8. **Customer Status badge colors duplicated in two places** (`customer_controller.py` had its own local palette that never actually called the shared `tier_engine` helper; `invoice_controller.py` used a different default via `build_status_color_map()`) — inconsistent with the central-theme direction. **Consolidated** into `theme.STATUS_TIER_PALETTE` / `theme.STATUS_STANDARD_COLOR`, both controllers now pass these explicitly into `build_status_color_map()`.

---

## 🐛 Known Open Items

1. Older invoices created before the `Paid/Unpaid/Partial` → `Paid/Due/Partial Due` → `Paid/Due/Partial Payment` renames still display their original saved status text — this is correct historical record-keeping, not a bug.
2. **Native Windows title bar coloring was explored and explicitly dropped** — DWM API only works on Windows 11 (build 22000+), not Windows 10; the app-wide mint-green `PAGE_BACKGROUND` theme was used instead as an OS-independent way to look distinct. No title-bar-coloring code remains in `main.py`.
3. `assets/fonts/NotoSansBengali-*.ttf` intentionally removed from the working zip to keep it small — falls back to Windows' `Nirmala.ttf` at runtime; only matters for PyInstaller bundling later.
4. **Dashboard, Invoice Terminal (cart/item tables), and History Ledger table** have not yet been migrated to `theme.configure_responsive_table()` — deferred pending confirmation the new responsive style is desired everywhere. Same fixed-pixel-column limitation as before applies to these specific tables only.
5. `SIDEBAR_COMPACT_HEIGHT_BREAKPOINT`, `SIDEBAR_LOGO_SIZE_COMPACT`, `SIDEBAR_BRAND_FONT_COMPACT` constants exist in `theme.py` but are currently **dead/unused** (the feature they powered was removed — see Responsive UI point #2). Harmless to leave; can be wired up again or deleted later.
6. `tier_engine.build_status_color_map()` still has hardcoded fallback defaults in its own signature (for callers that don't pass `palette`/`standard_color`) — both current callers always pass `theme`'s values explicitly, so this is a dormant fallback only, not currently exercised.

None else currently outstanding.

---

## 📂 Current Project Directory
```text
vermi_sales_app/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 8f6a5632b5e4_initial_schema_setup.py
│       ├── c4d8f2a91b6e_add_discount_and_paid_amount.py
│       ├── d7f3a2c8b915_add_less_adjustment.py
│       ├── e2a9c1f74d38_add_due_payment_chain.py
│       ├── f7c3d81a2e56_add_transport_charge.py
│       ├── a1b2c3d4e5f6_add_customer_types_tiers_settings.py   # NEW
│       └── g2h3i4j5k6l7_add_rank_hold_months.py                # NEW
├── assets/
│   ├── app_icon.ico
│   └── logo.png
├── src/
│   ├── config/
│   │   ├── company_config.py   # Client branding + INVOICE status colors
│   │   ├── pdf_styles.py       # Per-section PDF background theming
│   │   └── theme.py            # App-wide UI chrome + responsive layout helpers + Status badge palette
│   ├── controllers/
│   │   ├── customer_controller.py   # NEW
│   │   ├── dashboard_controller.py
│   │   ├── history_controller.py
│   │   ├── invoice_controller.py
│   │   ├── profile_controller.py
│   │   └── settings_controller.py   # NEW
│   ├── database/
│   │   ├── base_class.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── utils/
│   │   ├── asset_utils.py
│   │   ├── excel_exporter.py
│   │   ├── pdf_fonts.py
│   │   ├── pdf_generator.py
│   │   ├── tier_engine.py      # NEW — Customer Status computation
│   │   └── time_utils.py
│   └── views/
│       ├── customer_view.py         # NEW
│       ├── dashboard_view.py
│       ├── due_payment_dialog.py    # DuePaymentDialog + PaymentHistoryDialog
│       ├── history_view.py
│       ├── invoice_view.py
│       ├── main_window.py
│       ├── profile_view.py
│       └── settings_view.py         # NEW
├── .env
├── alembic.ini
├── requirements.txt
└── main.py
```

---

## 🎯 Global Development Rules (unchanged, +3 new)
1. **Strict Decoupling:** Views = GUI only. Business logic lives in Controllers/Utils.
2. **Robust Error Handling:** DB/file/image ops wrapped in `try/except` with `QMessageBox` feedback.
3. **Clean DB Sessions:** context managers / `try-finally`, no dangling connections. **Modals are always opened OUTSIDE a `with get_db_session()` block** — query needed data, close the session, *then* show the dialog; only open a fresh session afterward to write results. (Established convention; followed for every new dialog this session — `CustomerDialog`, `TierDialog`, `TypeDialog`.)
4. **Signature Storage:** signatures resized to max 200×80px PNG, stored as `BYTEA`, never as file paths.
5. **Asset Path Resolution:** always via `src/utils/asset_utils.py::get_asset_path()`.
6. **White-labeling:** all client-specific branding goes in `src/config/company_config.py` / `src/config/pdf_styles.py` — never hardcode in views/controllers/utils.
7. **PDF fonts:** never globally override `styles['Normal'].fontName` with a script-specific font — wrap only the specific glyphs that need it in inline `<font face="...">` markup.
8. **Responsive layouts:** avoid open-ended `QHBoxLayout`/`QVBoxLayout` rows for anything that can grow — use `QGridLayout` with a fixed shape, or wrap in a scroll area, or (for tables) use `theme.configure_responsive_table()`.
9. **App-wide UI theming:** all background/card/border/accent colors, responsive-table setup, and Status badge colors go through `src/config/theme.py` — never hardcode `#cbd5e1`/`white`/`#1abc9c`/tier-color literals directly in a view or controller. Semantic one-off button colors (success/danger/info-blue/purple-chain) are fine as local literals.
10. **Invoice immutability + due-payment chain:** once issued, an invoice's own stored fields are **never edited**. Later payments are recorded as new linked `Invoice` rows (`is_due_payment=True`). Always read/display `effective_*` properties for current truth.
11. **NEW — Customer selection is always explicit:** never silently create-or-overwrite a `Customer` row based on a typed phone/name match at invoice-issue time. Selection happens via the searchable picker or the dedicated "Add New Customer" flow — both on the Invoice Terminal and via the Customers page — never as a side effect of submitting an unrelated form.
12. **NEW — Status ("Tier") is always computed live, never stored:** any screen displaying a customer's Status must call `tier_engine.evaluate_customer_status()` fresh (once per page load/Refresh, not per-row/per-repaint) rather than reading/caching a stored value — this includes after a Settings change to tiers/grace/decay/hold, which must take effect immediately on next view without any migration or backfill.
13. **NEW — Responsive table setup call order:** `theme.configure_responsive_table(table, columns)` must be called **before** `table.setHorizontalHeaderLabels(...)` on any table — the reverse order silently discards header text (see Responsive UI point #5).

---

## 📦 Production Compiling (PyInstaller)
```bash
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="ChashiBondhuSuite" main.py
```
- `--onedir` (not `--onefile`) recommended for PyQt6 apps to avoid slow startup unpacking.
- `--add-data "assets;assets"` bundles the logo/icon/fonts folder into the `.exe`.
