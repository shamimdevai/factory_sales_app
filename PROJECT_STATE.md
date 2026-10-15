# Vermi-Composting Factory Invoice & Sales App (Project Specification & State)

> **Last updated:** 2026-10-15 — reflects the codebase after: the editable **Product catalog**, the **Rule #3 (DB-session vs. modal) audit/fix** across all controllers, the **Signature editor (resize + delete)**, **invoice backdating via a new `invoice_date` business-date column** (now driving every date-based screen/report), the optional **Customer Status snapshot on invoices**, and a custom **`TickCheckBox`** widget. Start new chats by uploading this file plus the current project zip (or the specific files you're working on).
>
> **Verification note:** code for the items above was delivered in chat as targeted edits / full-file replacements. **Confirmed by the owner:** all Alembic migrations through `j6k7l8m9n0o1` have been run; the Backdate, "Add Customer Status at Invoice" and Transport checkboxes all render with a black border and a visible tick mark (`TickCheckBox` works). Everything else (Products UI, Signature editor, `invoice_date` rewiring across Dashboard/History/Customers/tier_engine/PDF) should be treated as "delivered, owner-side end-to-end testing pending" — diff against the real files at the start of the next session before building on top of it.

---

## 📌 Project Overview
A professional Windows desktop application for a vermi-composting factory (branded **Chashi-Bondhu**), selling **Vermi-compost** and **Earthworms** (and any other products the admin defines). Replaces manual Excel invoicing with a PyQt6 desktop app backed by PostgreSQL, with PDF/Excel export and digital signatures. It provides a secure UI for entering transaction data, tracks database records, computes dashboard statistics, and includes full customer relationship management (customer directory, purchase-history pivot, a purchase-volume-based Status/loyalty-tier system), an **admin-editable product catalog**, and **backdated invoicing** with a clean separation between *business date* and *audit timestamp*.

---

## 🛠️ Tech Stack
- **OS Platform:** Windows 10/11 (target deployment)
- **Language:** Python 3.11
- **UI Framework:** PyQt6 (`Fusion` style + explicit light `QPalette`, centrally themed via `src/config/theme.py`)
- **Database:** PostgreSQL + SQLAlchemy ORM
- **Migrations:** Alembic (currently at **10 revisions** — see below). Migration SQL in `j6k7l8m9n0o1` uses Postgres-specific syntax (`INTERVAL '6 hours'`, `::date`) — fine since PostgreSQL is the only target.
- **Exports:** ReportLab (PDF), openpyxl (Excel)
- **Compiler:** PyInstaller (.exe bundling)
- **Env management:** python-dotenv (for local credential isolation)

---

## 🆕 Changes since the 2026-08-11 version (quick index)
1. **Product catalog** — new `Product` model/table, Settings → Products section, Invoice Terminal product dropdown is now data-driven; unit + default price pre-fill the sale form (both still editable per invoice). Replaced the 4 hardcoded products.
2. **Rule #3 audit** — every controller scanned; ~17 methods across 5 controllers fixed so no `QMessageBox`/`QDialog.exec()` ever runs inside a `with get_db_session()` block (details in "Controller DB-Session Audit").
3. **Signature editor** — Upload now opens a resize/zoom editor (live preview), new **✏️ Resize** (re-edit saved signature) and **🗑️ Delete** buttons. Image compositing moved into the View; controller only persists bytes.
4. **Backdating** — "Backdate this invoice" checkbox + date picker at the top of the Customer Details card. Writes a **new `invoice_date` (Date) column**; `created_at` is never touched.
5. **`invoice_date` is now the business/purchase date everywhere** — Dashboard (KPIs, period filters, Recent 10), History Ledger, Customer Purchase Summary "Last Purchase", `tier_engine.py` (period sums + grace/decay age), and all PDF "Date" lines.
6. **Customer Status snapshot on invoice** — optional checkbox "Add Customer Status at Invoice"; stores a text snapshot in new `Invoice.customer_status_snapshot`, printed in the sale PDF's Bill-To block.
7. **`theme.TickCheckBox`** — custom self-painting checkbox (black border + real tick mark) used for all 3 checkboxes on the Invoice Terminal.
8. Alembic: 3 new revisions (`h4i5j6k7l8m9`, `i5j6k7l8m9n0`, `j6k7l8m9n0o1`).

---

## ⚠️ Correction vs. earlier project-state versions
An earlier version of this document incorrectly stated that invoices used a free-text `customer_name` field with no dedicated `Customer` model. That was wrong — the actual codebase has had a `Customer` model and a **required** (`nullable=False`) `Invoice.customer_id` FK since the **initial migration** (`8f6a5632b5e4`).

---

## ✅ Current Feature State

### Dashboard (`dashboard_view.py` + `dashboard_controller.py`)
- KPI tiles (Total Revenue, Compost kg, Worms kg, Total Invoices).
- **Period selector** (Row 1, light-blue tinted `QFrame`): dropdown **View:** `Today` (default) / `Month` / `Year` / `Date Range` (From/To) / `All`, plus a **🔍 View** button. Only the input(s) relevant to the selected mode are visible.
- **All period scoping is now driven by `Invoice.invoice_date`** (business/purchase date), not `created_at`. A backdated invoice reports under its real transaction date.
- `DashboardController._resolve_period()` was rewritten this session: it now returns **plain `date` objects** `(start_date, end_date, label)`, inclusive on both ends (`None, None` for "All"). The old `datetime` + `time.min/time.max` start/end-of-day boundary tricks are gone because `invoice_date` has no time component. Filters use `Invoice.invoice_date.between(start_date, end_date)`.
- **"All"** mode shows `Showing: All Time (earliest to latest invoice_date)`, queried live, excluding due-payment records; falls back to `All Time (No records yet)`.
- KPI cards show a small **"Showing: ..."** caption confirming the active period.
- **"Recent 10 Records"** table: global (not period-filtered), includes due-payment records inline. **Now ordered by `invoice_date DESC, id DESC`** (the `id` tiebreaker keeps same-day ordering deterministic) and displays `invoice_date` (plain `YYYY-MM-DD`, no UTC offset conversion needed). *(Owner explicitly chose this over keeping it on `created_at`.)*
- Compost/Worms kg aggregation matches product names by **keyword** (`%compost%`, `%worm%`), joined to `Invoice` so period scoping and due-payment exclusion apply. See Known Open Items #3 — this keyword approach is now a limitation because products are user-defined.
- Imports cleaned: only `calendar` and `datetime.date` are needed; `to_local_str`/`time` no longer used here.
- **Not yet migrated** to `theme.configure_responsive_table()` — still hand-set column widths.

### Invoice Terminal (`invoice_view.py` + `invoice_controller.py`)
Financial fields, in calculation order:
```
taxable_amount = subtotal − discount
VAT_amount     = taxable_amount × VAT_rate
grand_total    = taxable_amount + VAT_amount + transport_charge − less_adjustment   (clamped ≥ 0)
due_amount     = grand_total − paid_amount                        (computed property, not stored)
```
- **Discount**: flat amount, applied before VAT. **VAT**: user-entered %, default 0%. **Transport**: optional flat add-on via checkbox (`chk_transport`), only a PDF line if checked at issue time (`show_transport_charge`, immutable). **Less Adjustment**: flat deduction after VAT/Transport.
- **Payment Status** dropdown: `Paid`, `Due`, `Partial Payment`. Status/paid/due amounts color-coded via `company_config.resolve_status_color()`.
- Metrics box uses `QGridLayout`. Cart table uses fixed column widths with native scrollbars.

**Customer Details card (top to bottom):**
1. **Backdate row** *(new)* — `chk_custom_date` ("Backdate this invoice", a `theme.TickCheckBox`) + `date_custom` (`QDateEdit`, calendar popup, `yyyy-MM-dd`). The date picker is disabled until the box is ticked; max date = **today** (backdating only — **no post-dating**, a deliberate design choice); unticking resets it to today. `get_invoice_date()` returns a python `date` or `None`.
2. **Searchable combo** (`combo_customer`, editable, `MatchContains`, case-insensitive) — type any part of name or phone. Placeholder `"Search Customer by Name or Phone"` doubles as the label.
3. **Read-only info line**: `Phone: ... | Type: ... | Status: ...` (from data already in the combo's `itemData`; no extra DB round-trip).
4. **"Add Customer Status at Invoice"** *(new)* — `chk_include_status` (`TickCheckBox`) directly under the info line. Visible only while a real customer is selected; **reset to unchecked every time the selected customer changes**, when "+ New" is clicked, and after an invoice is issued. When ticked, the currently shown Status text (`_current_customer_status_text`) is sent as `customer_status_snapshot`.
5. **"+ New"** button → inline "New Customer" panel (Name*/Phone*/Email/Address/Type + Add/Cancel); registers and auto-selects the customer (`select_customer_by_id`).
- Card is pinned to natural top-aligned height (`QSizePolicy.Fixed` + `AlignTop` + `left_panel.addStretch()`).
- `InvoiceController.refresh_customer_list()` and **`refresh_product_list()`** run on controller construction **and** every time `main_window._switch_view` switches to the Invoice page (index 1), so edits made on Customers/Settings appear without a restart.
- Customer selection is always explicit (pick from list or "+ New") — no get-or-create-by-phone overwriting (Rule #11).

**Add Products card — now data-driven (new this session):**
- `combo_product` is populated by `InvoiceView.populate_products(products)` from the `Product` table (sorted by name). The hardcoded 4-item list is gone.
- Selecting a product runs `_on_product_changed()`: sets `spin_qty` suffix to the product's unit and `spin_price` to its default price. **Both remain freely editable per sale.**
- `spin_price` range is now `0.01–100000` (was `1.0`) to allow cheap items.
- Empty catalog → "Add to Invoice" shows a warning pointing to Settings.
- Signal is now `add_item_requested(str, float, float, str)` = (name, qty, unit price, **unit**). `InvoiceController.add_item_to_cart(name, qty, price, unit="kg")` stores `unit` in the **in-memory cart item dict only**.
- Cart table's Qty column now shows `"{qty:.2f} {unit}"` instead of a hardcoded `kg`.
- **Unit is NOT persisted** to `InvoiceItem` (no column) — see Known Open Items #1.

**Issuing an invoice (`commit_invoice`, restructured for Rule #3):**
1. Empty-cart guard.
2. Short read session: verify the selected `Customer` exists → if not, close session, *then* show the error.
3. Single write session: get/create operator `User`, compute financials, create `Invoice` (+ `customer_status_snapshot`; + `invoice_date` **only if** a custom date was supplied — otherwise the column default applies), create `InvoiceItem` rows. **No manual `session.commit()`** — `get_db_session()` commits when the `with` block exits normally.
4. After the session closes: success `QMessageBox`, clear cart, `clear_inputs()`, enable Download PDF.
- `add_new_customer_inline()` does its duplicate-phone check in its own short session, shows the warning after it closes, then inserts in a second session.
- Submit payload keys: `customer_id, payment_status, discount, tax_rate, less_adjustment, transport_charge, show_transport_charge, paid_amount, invoice_date (date|None), customer_status_snapshot (str|None)`.

### Due-Payment Chain (`models.py`, `invoice_controller.py`, `history_view.py`/`history_controller.py`, `due_payment_dialog.py`, `pdf_generator.py`)
Once issued, an invoice is **immutable**. `Due`/`Partial Payment` invoices track later payments as linked `is_due_payment=True` rows (`parent_invoice_id` → root). Computed properties `effective_paid_amount` / `effective_due_amount` / `effective_status` remain the source of truth everywhere.
- **Date handling:** due-payment rows get `invoice_date` automatically (column default = their own creation day, local); they are **never backdatable** (the checkbox only exists on the Invoice Terminal).
- **Chronological ordering of a chain still sorts on `created_at`** (full timestamp) in `history_controller.handle_view_payment_history` and `pdf_generator` — `invoice_date` has no time-of-day, so same-day payments could not be ordered by it. Only the **displayed** dates use `invoice_date`.

### Customer Management (`customer_view.py` + `customer_controller.py`)
Two tabs, unchanged in layout:
- **Customer Directory**: Name, Phone, Email, Type, **Status** badge, Actions (✏️ Edit / 🧾 View Ledger). `CustomerDialog` (Name*/Phone*/Email/Address/Type); duplicate phone checked client-side and by DB `UNIQUE`.
- **Purchase Summary (pivot)**: Total Invoices (root sales only), Total Grand Total, Total Discount, Total Paid, Total Due, **Last Purchase Date**, Compost (kg), Worms (kg), Actions. Frozen TOTAL footer (`table_pivot_totals`) glued to the main table via `sectionResized` + scrollbar sync.
- **"Last Purchase Date" now = `max(inv.invoice_date)`** formatted `%Y-%m-%d` (was `created_at` through `to_local_str`).
- `CustomerController.refresh_all()` computes both tabs in one pass per page load/Refresh — never per-row/per-repaint (Status runs several queries per customer).
- **Rule #3 fixes:** `add_customer` and `edit_customer` now do duplicate-phone / "not found" checks in short read sessions and only show `QMessageBox`es after the session closes; writes happen in a separate session.
- Compost/Worms kg columns also use keyword matching on `product_name` (Known Open Items #3).

### Status / Tier System (`src/utils/tier_engine.py`) — rewritten to date-based math
Status (Silver/Golden/Platinum/… — admin-defined) is **never stored** on the `Customer` row; computed live (same philosophy as `Invoice.effective_status`).

> **Naming note:** internally "Tier" (`CustomerTier`, `tier_engine.py`) to avoid confusion with `Invoice.payment_status`/`effective_status`. Every **UI-facing** label must say **"Status"**.

**Everything is now driven by `Invoice.invoice_date`** — a backdated invoice counts toward the tier period and decay clock of its *real* purchase date.

**`evaluate_customer_status(customer_id, session, now=None)`:**
- `now` accepts a `date` **or** a `datetime` (a datetime is normalized with `.date()`); default `date.today()`.
1. **Base Status (with HOLD):** walk tiers highest→lowest rank; for each, walk backward through that tier's own periods (calendar month or year) from the current period up to `rank_hold_months` back. The most recent period whose root-sale `grand_total` sum meets the threshold is the anchor; the customer holds that tier until `rank_hold_months` after it. Newest-first scan means requalifying resets the anchor. None found → **"Standard"**.
2. **Decay (independent of hold):** find the oldest unpaid root invoice by `invoice_date ASC, id ASC` with `effective_due_amount > 0.001`; `age_days = (today − invoice_date).days`.
   - `age_days ≤ grace_days` → no penalty; `≤ grace_days + decay_step_days` → still none; beyond that, **1 rank drops per additional fully-elapsed decay step**, floored at "Standard", degrading by **list position** (robust to rank gaps).
3. **Final Status** = base tier − decay steps.
- **Window math (new):** `_month_window(year, month, today)` / `_year_window(year, today)` return `(start_date, end_date)` **inclusive on both ends**, with `end_date` clipped to `today` for the in-progress period. `_sum_grand_total` filters `invoice_date >= start_date AND invoice_date <= end_date`. (The old exclusive-upper-bound datetime logic could not express "include today" with a date-only column, hence the rewrite.)
- `build_status_color_map(session, standard_color, palette)` — shared badge-color helper (assign by **rank position**, highest tier → `palette[0]`). Callers must pass `theme.STATUS_TIER_PALETTE` / `theme.STATUS_STANDARD_COLOR` explicitly; this module has zero UI/theme imports by design.
- **Performance:** `_compute_base_tier` runs multiple queries per tier per customer. Call only once per page load/Refresh — never per-row/per-repaint.

### Settings Page (`settings_view.py` + `settings_controller.py`) — now 4 sections
1. **Customer Status Tiers** — table (Status Name, Min. Amount, Period, Reorder ▲▼, Actions); `TierDialog`. Reordering swaps `rank` via a temporary sentinel (`-1`) to avoid tripping `UNIQUE(rank)`. Deleting a tier is safe.
2. **Customer Types** — Add/Edit/Delete list (`TypeDialog`, case-insensitive duplicate check). Deleting a type in use `SET NULL`s it on customers.
3. **Products** *(new)* — table (Product Name, Unit, Default Price, Actions) + "+ Add Product" (responsive header button, in the `install_responsive_buttons` list alongside Add Tier / Add Type).
   - `ProductDialog(parent, name="", unit="kg", default_price=0.0)`: Name `QLineEdit`; **Unit = editable `QComboBox`** (presets `kg, g, L, ml, pcs, box, bag, ton`, or type a custom one); Default Unit Price `QDoubleSpinBox` (currency-symbol prefix from `company_config`, range `0.01–100,000,000`, 2 decimals). Validates non-empty name and unit.
   - Controller: `_refresh_products`, `add_product`, `edit_product`, `delete_product` (case-insensitive duplicate-name check; delete confirmation notes historical invoices are unaffected). All Rule-#3 compliant.
   - Deleting/renaming a product **never touches historical invoices** (`InvoiceItem.product_name` is a text snapshot, no FK).
4. **Status Rules** — three `QSpinBox`es (Grace Period days, Decay Step days, Status Hold Period months) on the singleton `AppSettings` row (`id=1`).
- Settings controller methods fixed for Rule #3: `edit_tier`, `edit_type`, `edit_product` (read → close → dialog → [dup check → close] → write), `add_type`/`add_product` (dup-check session closes before the warning), `delete_tier`/`delete_type`/`delete_product` (read name → close → confirm → reopen to delete). `add_tier` was already compliant.

### Sales History Ledger (`history_view.py` / `history_controller.py`)
3 filter modes: **Quick Search** (default; debounced ~300ms; matches Invoice ID, Customer Name, Phone, **Date (invoice_date, `YYYY-MM-DD`)**, effective Status, Grand Total, effective Due), **Date Range** (explicit 🔍 button), **Status** (explicit button; filtered in Python since `effective_status` is computed). **✖ Clear Search** resets everything. Single **⬇ Export** click-menu (PDF / Excel) reusing the active filter via `_get_filtered_records()`. Programmatic `customer_id` mode via `apply_customer_filter()` / `show_customer_ledger()` ("View Ledger" from Customers page).
- **Now fully `invoice_date`-based:** all `order_by` calls use `Invoice.invoice_date.desc(), Invoice.id.desc()` (id tiebreaker for stable same-day ordering); Date Range uses `Invoice.invoice_date.between(start_date, end_date)` with plain dates from `QDate.toPyDate()`; the table's Date column shows `invoice_date`. Imports of `datetime`/`time`/`to_local_str` are no longer needed in this controller.
- Table: Invoice ID, Customer, Date, Discount, Grand Total, Status, Due, Actions (📄/💰/🧾).
- Rule #3 fixes: `handle_pay_due` and `handle_view_payment_history` now close their read session before any "not found" `QMessageBox`; the dialogs themselves (`DuePaymentDialog`, `PaymentHistoryDialog`) were already opened outside sessions.
- **Not yet migrated** to `theme.configure_responsive_table()`.

### Operator Profile & Signature (`profile_view.py` + `profile_controller.py`) — reworked this session
- **Signature storage rule (unchanged intent):** always a PNG at **fixed 200×80px** (`theme.SIGNATURE_MAX_WIDTH/HEIGHT`) in `User.digital_signature` (`BYTEA`, nullable), never a file path. The output is now always composited onto a **transparent 200×80 canvas**.
- **`SignatureEditorDialog`** (pure GUI, in `profile_view.py`): takes a `QImage`; shows a 3× magnified live preview; **scale slider 20%–200%** of "best fit" (default 100%) — below 100% = centered with transparent padding (fixes "too big/edge-to-edge"), above 100% = zoomed with overflow clipped at the canvas edge (fixes "too small because of blank margins in the source photo"); "Reset to Best Fit"; Save/Cancel. `get_signature_bytes()` returns the final PNG bytes.
- **Buttons on the Signature card:** **📁 Upload** (file picker → editor), **✏️ Resize** (re-opens the editor on the *currently saved* signature, no re-upload needed), **🗑️ Delete** (confirmation `QMessageBox` lives in the View since it touches no DB). Resize/Delete are **disabled** until a signature exists.
- **Signals:** `save_profile_requested(str,str,str,str)` (unchanged), **`signature_saved(bytes)`** (replaces the old `signature_uploaded(str)`), **`signature_delete_requested()`**.
- **`ProfileView.set_signature_data(png_bytes | None)`** replaces `set_signature_preview(pixmap)`: stores the bytes, updates the preview label, toggles Resize/Delete.
- **Controller** shrank to persistence only (Rule #1 — image editing is GUI work): `load_operator_profile`, `update_user_profile`, **`save_signature(png_bytes)`**, **`delete_signature()`** (sets `digital_signature = None`). `process_and_save_signature` was removed. All methods Rule-#3 compliant, no manual `session.commit()`.
- `pdf_generator.py` already skips the signature when falsy, so Delete needs no PDF change.

### Database (`models.py`)
`Invoice` fields: `customer_id` (FK, NOT NULL), `total_amount` (subtotal), `discount_amount`, `tax_rate` (VAT), `less_adjustment`, `transport_charge`, `show_transport_charge`, `grand_total`, `paid_amount`, `payment_status`, `parent_invoice_id`, `is_due_payment`, **`created_at`**, **`invoice_date`** *(new)*, **`customer_status_snapshot`** *(new)*; computed properties `due_amount`, `effective_paid_amount`, `effective_due_amount`, `effective_status`.

**The two date fields (important — don't conflate them):**
| Field | Type | Meaning | Ever overridden? |
|---|---|---|---|
| `created_at` | `DateTime` (naive UTC, indexed) | **True system timestamp** of when the row was inserted. Pure audit fact. | **Never** |
| `invoice_date` | `Date` (local calendar day, indexed, **NOT NULL**) | **Business/purchase date** — what the PDF prints and what every report/filter/sort/tier calculation uses. | Only via the Invoice Terminal's "Backdate this invoice" (root sale invoices only) |

- `invoice_date` default is a Python callable on the column: `(datetime.utcnow() + timedelta(hours=6)).date()` — so **every** insert path (sale invoices, due-payments, anything future) gets today's local date automatically with zero extra code. `models.py` now imports `timedelta` and `Date`.
- **A row is "backdated" iff `invoice_date` ≠ the local calendar date of `created_at`.** There is intentionally **no `is_backdated` flag and no UI indicator** (owner: "keep it only in database for now"). Query later if needed.
- `customer_status_snapshot` = `String(50)`, nullable. Plain text snapshot of the customer's Status label (e.g. "Golden") taken at issue time, **only** when the checkbox was ticked; always NULL for due-payment rows. Same pattern as `InvoiceItem.product_name`. It does **not** change how Status is computed (Rule #12 untouched).

**Other models:**
- `Customer` — `customer_type_id` (FK → `customer_types`, nullable, `ON DELETE SET NULL`); `name`, `phone` (unique), `email`, `address`, `created_at`.
- `CustomerType` — `id`, `name` (unique).
- `CustomerTier` — `id`, `name`, `min_amount`, `period` (`"monthly"`/`"yearly"`), `rank` (unique). UI label = "Status".
- `AppSettings` — singleton (`id=1`): `grace_days`, `decay_step_days`, `rank_hold_months`.
- **`Product`** *(new)* — `id`, `name` (unique, String 100), `unit` (String 20, default `"kg"`), `default_price` (Float, default 0). **Catalog only — nothing references it by FK.**

**Migrations (run `alembic upgrade head` — `init_db()` alone won't add columns to existing tables). Chain order matters:**
1. `8f6a5632b5e4` — initial schema (incl. `Customer` + required `Invoice.customer_id`)
2. `c4d8f2a91b6e` — `discount_amount`, `paid_amount`
3. `d7f3a2c8b915` — `less_adjustment`
4. `e2a9c1f74d38` — `parent_invoice_id`, `is_due_payment`
5. `f7c3d81a2e56` — `transport_charge`, `show_transport_charge`
6. `a1b2c3d4e5f6` — `customer_types`, `customer_tiers`, `app_settings`, `customers.customer_type_id`; seeds Retail/Wholesale/Distributor/Farmer and Silver 10,000 / Golden 50,000 / Platinum 100,000 (monthly, ranks 1–3)
7. `g2h3i4j5k6l7` — `app_settings.rank_hold_months` (default 6)
8. **`h4i5j6k7l8m9`** — creates `products` (+ `ix_products_id`); **seeds** Premium Vermi-Compost, Organic Earthworm Castings, Compost Starter Culture, Liquid Bio-Fertilizer — each `kg`, `25.0` (matches the old spin default); admin-editable afterward, never re-seeded
9. **`i5j6k7l8m9n0`** — adds `invoices.customer_status_snapshot` (`String(50)`, nullable)
10. **`j6k7l8m9n0o1`** — adds `invoices.invoice_date`: add nullable → create index `ix_invoices_invoice_date` → **backfill** `UPDATE invoices SET invoice_date = (created_at + INTERVAL '6 hours')::date` → set `NOT NULL`. Existing rows therefore get their local creation day, so all historical reports stay unchanged.

### PDF Invoice Engine (`pdf_generator.py`)
Header logo, two layouts dispatched by `is_due_payment` (`_build_sale_invoice_pdf` / `_build_due_payment_pdf`), Bengali `৳` glyph fix (inline `<font>` wrap only), dynamic `num_summary_rows` for the optional Transportation row, fixed footer, theme-driven section backgrounds via `src/config/pdf_styles.py`.
Changes this session:
- Sale invoice **"Date:"** → `invoice.invoice_date.strftime('%Y-%m-%d')`.
- Sale invoice **Bill-To block** gains `Customer Status: <snapshot>` **only if** `customer_status_snapshot` is set (plain, no color-coding).
- Due-payment receipt's own **"Date:"** → `invoice.invoice_date`; **"originally issued on"** → `root.invoice_date`; **last-payment date** in the trail note → `sorted_payments[-1].invoice_date` (the *sort* still uses `created_at`).
- Due-payment PDF does not show the status snapshot (never set on those rows).
- Signature rendered at 120×45 (unchanged — see Known Open Items #4).
- **Item quantity still prints a hardcoded `"{qty:.2f} kg"`** — see Known Open Items #1.

### Timezone (`src/utils/time_utils.py`)
`to_local_str(dt)` (fixed +6h offset, `LOCAL_UTC_OFFSET_HOURS = 6`) is still used for **`created_at`** (naive UTC) wherever a true timestamp must be shown. **`invoice_date` is already a local calendar date — never pass it through `to_local_str`; format it directly** (`.strftime("%Y-%m-%d")`).

### White-labeling (`src/config/company_config.py`)
Unchanged. Client branding only — name, address, contact info, currency symbol, logo/icon paths, `STATUS_COLORS`/`resolve_status_color()` (for **invoice payment status**; not the Customer Status/tier colors, which live in `theme.py`).

---

## 🎨 Central UI Theme — `src/config/theme.py`
Single source of truth for static styles **and** responsive layout helpers/widgets.

**Existing:** `PAGE_BACKGROUND`, `SIDEBAR_BACKGROUND`, `SIDEBAR_HOVER`, `CARD_BACKGROUND`, `BORDER_COLOR` (`#CBD5E1`), `ACCENT`/`ACCENT_DARK`, `TEXT_PRIMARY`, `TEXT_MUTED`; `card_frame_style()`, `input_style()` (auto-appends `combobox_dropdown_style()` for `"QComboBox"`; also used for `"QDateEdit"`, `"QDoubleSpinBox"`), `combobox_dropdown_style()`, `TOTALS_ROW_BACKGROUND` + `totals_row_style()`, `STATUS_TIER_PALETTE` + `STATUS_STANDARD_COLOR` (single source for Customer Status badge colors, by rank position), `TABLE_MIN_SECTION_SIZE` (60) + `configure_responsive_table(table, columns, ...)`, `SIDEBAR_WIDTH` (240) + `SIDEBAR_LOGO_WIDTH_RATIO` + `sidebar_logo_size()`, `SIDEBAR_BRAND_FONT_SIZE`, `HEADER_BUTTON_COMPACT_BREAKPOINT` + `install_responsive_buttons(...)`.

**New this session:**
- `SIGNATURE_MAX_WIDTH = 200`, `SIGNATURE_MAX_HEIGHT = 80` — the storage ceiling for signatures (Rule #4); read by `SignatureEditorDialog`.
- **`TickCheckBox(QCheckBox)`** — a self-painting checkbox. Its `paintEvent` calls `super().paintEvent()` (label/focus rect) then paints its own indicator box on top (`QStyleOptionButton` + `SE_CheckBoxIndicator` rect, 2px **black** border, `CARD_BACKGROUND` fill) and, when checked, an `ACCENT`-colored **tick mark** drawn as two `QPainter` lines. No assets, no files, no network, no stylesheet needed for the indicator. Required imports in `theme.py`: `QCheckBox, QStyle, QStyleOptionButton` (QtWidgets), `QPainter, QPen, QColor` (QtGui), `Qt, QRectF, QPointF` (QtCore).
  - **Why it exists (don't "simplify" it back):** (a) `BORDER_COLOR` is too light to read as a checkbox outline on white cards. (b) **Qt limitation:** as soon as *any* QSS rule targets `QCheckBox::indicator`, Qt stops drawing its native checkmark for *every* state, so "custom border + native tick" is impossible via QSS. (c) A bundled SVG tick (`assets/checkbox_tick.svg`) was tried and **dropped** — unnecessary dependency. (d) The earlier `checkbox_style()` helper was **removed**. (e) Gotcha: mixing bare `property: value;` declarations with `QCheckBox::indicator {...}` selector blocks in one `setStyleSheet()` string makes Qt silently drop the indicator rule — another reason QSS-based indicator styling was abandoned.
  - Used by `chk_transport`, `chk_custom_date`, `chk_include_status`. Label/container styling is still set via a normal `QCheckBox { ... }` stylesheet on each instance (no indicator rules in it).

**Applied so far (responsive helper):** Customers page, Settings page (Tiers/Types/Products tables + header buttons), sidebar. **Not yet applied:** Dashboard, Invoice Terminal (cart/item tables), History Ledger table.

---

## 📱 Responsive UI — what was actually broken and fixed (historical, unchanged)
1. **Fixed-pixel table columns never responded to resize** → `theme.configure_responsive_table()` (baseline widths first, then `Stretch`/`Fixed` — preserves proportions).
2. **Sidebar overlap/ghosting at small sizes** → sidebar wrapped in its own `QScrollArea` (`sidebar_scroll`); the dynamic logo/font-shrinking code was removed as unnecessary.
3. **Logo/brand not centered** → stretch-padded `QHBoxLayout` (`addStretch()` / widget / `addStretch()`).
4. **Customer Details card rendering as a large blank box** → `QSizePolicy.Fixed` vertically + `AlignTop` + `left_panel.addStretch()`.
5. **Table header labels vanishing** → call `configure_responsive_table()` **before** `setHorizontalHeaderLabels()` (a 0-column table silently discards labels).
6. **Header buttons not compacting** → removed page-level `setMinimumWidth` on `CustomerView`/`SettingsView`.
7. **Compact icon-only buttons had no discoverability** → full label set as tooltip while compacted.
8. **Status badge colors duplicated** → consolidated into `theme.STATUS_TIER_PALETTE` / `STATUS_STANDARD_COLOR`.

---

## 🔒 Controller DB-Session Audit (Rule #3) — completed 2026-10-15
**Why Rule #3 matters concretely:** `get_db_session()` calls `session.commit()` only when the `with` block *exits normally*. A modal shown inside the block leaves the transaction uncommitted and the connection checked out for as long as the user takes to click.

**Fixed (modal moved outside the session; writes in a separate short session):**
- `invoice_controller.py`: `add_new_customer_inline`, `commit_invoice` (customer-not-found + the success dialog that previously sat *before* the commit completed)
- `customer_controller.py`: `add_customer`, `edit_customer`
- `settings_controller.py`: `edit_tier`, `edit_type`, `edit_product`, `add_type`, `add_product`, `delete_tier`, `delete_type`, `delete_product`
- `history_controller.py`: `handle_pay_due`, `handle_view_payment_history`
- `profile_controller.py`: `update_user_profile`, signature save/delete (the old `process_and_save_signature` was replaced)
- Redundant manual `session.commit()` calls inside `with` blocks were removed where touched.

**Audited and already compliant:** `settings_controller.add_tier`; `history_controller._get_filtered_records` / `load_records` / both exports / `reprint_single_invoice`; `dashboard_controller`; `InvoiceController.record_due_payment` (raises; callers show modals); `InvoiceController.generate_invoice_pdf`.

**Standard shape to copy:** short read session → copy needed values into locals → close → modal/dialog → (if writing) fresh short session → refresh UI. Use a sentinel (`None`) for "not found" and test it *after* the `with` block.

---

## 🐛 Known Open Items

1. **Per-item unit is not persisted.** Products now carry units (`kg`, `pcs`, `L`, …) and the cart shows the right unit in-session, but `InvoiceItem` has **no unit column**, so **`pdf_generator.py` still prints `"{qty:.2f} kg"` for every item row** (and the Excel/ledger side never had units). A non-kg product will therefore show "kg" on the PDF. *Fix (not done):* add `InvoiceItem.unit` (String 20, nullable, default `"kg"`) via a new migration, save `cart_item["unit"]` in `commit_invoice`, and print `item.unit` in both PDF builders.
2. **Dashboard/pivot kg totals sum raw quantity regardless of unit.** See #3.
3. **"Compost kg" / "Worms kg" are keyword-based** (`product_name` contains `compost` / `worm`, case-insensitive) in `dashboard_controller.py` and `customer_controller.py`. Since products are now user-defined, a product must have "compost"/"worm" in its name to be counted, and a non-kg product whose name matches would be mis-summed. A more robust design (e.g. a `Product.category` field) was not built.
4. **Signature aspect ratio:** stored canvas is 200×80 (2.5:1) but `pdf_generator.py` renders it at fixed 120×45 (≈2.67:1), a ~7% horizontal stretch. Suggested fix: render at 120×48 (or 112×45).
5. **Timezone assumptions are duplicated, not centralized:** `models.py`'s `invoice_date` default and migration `j6k7l8m9n0o1` hardcode `+6 hours`, while `time_utils.LOCAL_UTC_OFFSET_HOURS` is the canonical constant. Also, `DashboardController` "Today" and `tier_engine` use `date.today()` (the PC's clock) whereas the `invoice_date` default uses fixed UTC+6 — identical on a Bangladesh-timezone machine, but would disagree on a PC set to another timezone.
6. **Backdate range:** date picker max = today (no post-dating). Deliberate; change `date_custom.setMaximumDate(...)` if post-dating is ever needed.
7. **Backdated invoices are invisible in the UI by design** (DB-only; compare `invoice_date` vs local date of `created_at`). If an audit view is ever wanted, no schema change is needed.
8. **`customer_status_snapshot` appears only on the sale-invoice PDF**, plain text, and **not** in the History Ledger/Excel.
9. **Possibly-unused imports after the `invoice_date` rewiring** (harmless; verify and tidy): `to_local_str` in `pdf_generator.py` / `customer_controller.py` (check other call sites first), `timedelta` in `tier_engine.py`, any leftover `datetime`/`timedelta`/`LOCAL_UTC_OFFSET_HOURS` imports in `invoice_controller.py` from the abandoned `created_at`-override approach.
10. Older invoices created before the `Paid/Unpaid/Partial` → `Paid/Due/Partial Due` → `Paid/Due/Partial Payment` renames still display their original saved status text — correct historical record-keeping, not a bug.
11. **Native Windows title bar coloring was explored and dropped** (DWM API Windows 11 only); the mint-green `PAGE_BACKGROUND` is used instead.
12. `assets/fonts/NotoSansBengali-*.ttf` intentionally removed from the working zip; falls back to Windows' `Nirmala.ttf` at runtime; only matters for PyInstaller bundling.
13. **Dashboard, Invoice Terminal (cart/item tables), History Ledger table** not yet migrated to `theme.configure_responsive_table()`.
14. `SIDEBAR_COMPACT_HEIGHT_BREAKPOINT`, `SIDEBAR_LOGO_SIZE_COMPACT`, `SIDEBAR_BRAND_FONT_COMPACT` in `theme.py` are dead/unused (harmless).
15. `tier_engine.build_status_color_map()` keeps hardcoded fallback defaults in its signature; both callers pass `theme` values explicitly, so the fallback is dormant.
16. **Zip contents note:** earlier uploads of the project zip lacked `main.py`, `requirements.txt`, `alembic.ini`, and `assets/`; this doc's directory tree describes the full project.

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
│       ├── a1b2c3d4e5f6_add_customer_types_tiers_settings.py
│       ├── g2h3i4j5k6l7_add_rank_hold_months.py
│       ├── h4i5j6k7l8m9_add_products.py                          # NEW
│       ├── i5j6k7l8m9n0_add_invoice_customer_status_snapshot.py  # NEW
│       └── j6k7l8m9n0o1_add_invoice_date.py                      # NEW
├── assets/
│   ├── app_icon.ico
│   └── logo.png
├── src/
│   ├── config/
│   │   ├── company_config.py   # Client branding + INVOICE status colors
│   │   ├── pdf_styles.py       # Per-section PDF background theming
│   │   └── theme.py            # UI chrome, responsive helpers, Status palette, SIGNATURE_MAX_*, TickCheckBox
│   ├── controllers/
│   │   ├── customer_controller.py
│   │   ├── dashboard_controller.py   # date-based period math (invoice_date)
│   │   ├── history_controller.py     # invoice_date ordering/filtering/display
│   │   ├── invoice_controller.py     # products, unit in cart, backdate/status snapshot, Rule #3
│   │   ├── profile_controller.py     # persistence-only signature save/delete
│   │   └── settings_controller.py    # tiers, types, PRODUCTS, rules
│   ├── database/
│   │   ├── base_class.py
│   │   ├── connection.py
│   │   └── models.py                 # + Product, Invoice.invoice_date, Invoice.customer_status_snapshot
│   ├── utils/
│   │   ├── asset_utils.py
│   │   ├── excel_exporter.py
│   │   ├── pdf_fonts.py
│   │   ├── pdf_generator.py          # invoice_date lines + Customer Status line
│   │   ├── tier_engine.py            # date-based windows / decay
│   │   └── time_utils.py
│   └── views/
│       ├── customer_view.py
│       ├── dashboard_view.py
│       ├── due_payment_dialog.py     # DuePaymentDialog + PaymentHistoryDialog
│       ├── history_view.py
│       ├── invoice_view.py           # backdate row, status checkbox, dynamic products, TickCheckBox
│       ├── main_window.py            # Invoice page switch → refresh_customer_list + refresh_product_list
│       ├── profile_view.py           # SignatureEditorDialog + Upload/Resize/Delete
│       └── settings_view.py          # + ProductDialog, Products box
├── .env
├── alembic.ini
├── requirements.txt
└── main.py
```
*(No new asset files. `assets/checkbox_tick.svg` was proposed and dropped; delete it if it was ever created.)*

---

## 🎯 Global Development Rules
1. **Strict Decoupling:** Views = GUI only (including GUI *work* such as image scaling/compositing — e.g. `SignatureEditorDialog`); business logic and persistence live in Controllers/Utils. A View may show a confirmation `QMessageBox` when no DB is involved.
2. **Robust Error Handling:** DB/file/image ops wrapped in `try/except` with `QMessageBox` feedback.
3. **Clean DB Sessions + modals outside sessions:** context managers / `try-finally`, no dangling connections. **Never show a `QMessageBox` or `QDialog.exec()` inside a `with get_db_session()` block** — read what you need into locals, close the session, *then* show the modal, and only open a fresh session afterward to write. `get_db_session()` commits automatically on normal exit, so **don't call `session.commit()` manually inside it**. (Fully audited 2026-10-15 — see "Controller DB-Session Audit".)
4. **Signature Storage:** PNG, fixed 200×80 (`theme.SIGNATURE_MAX_WIDTH/HEIGHT`), stored as `BYTEA`, never as file paths.
5. **Asset Path Resolution:** always via `src/utils/asset_utils.py::get_asset_path()`.
6. **White-labeling:** client-specific branding only in `src/config/company_config.py` / `pdf_styles.py`.
7. **PDF fonts:** never globally override `styles['Normal'].fontName`; wrap only specific glyphs in inline `<font face="...">`.
8. **Responsive layouts:** avoid open-ended `QHBoxLayout`/`QVBoxLayout` rows for anything that can grow — use a fixed-shape `QGridLayout`, a scroll area, or `theme.configure_responsive_table()` for tables.
9. **App-wide UI theming:** colors, responsive-table setup, Status badge colors, and widget appearance go through `src/config/theme.py` — never hardcode `#cbd5e1`/`white`/`#1abc9c`/tier-color literals in a view/controller. Semantic one-off button colors are fine locally.
10. **Invoice immutability + due-payment chain:** an issued invoice's stored fields are never edited; later payments are new linked `Invoice` rows (`is_due_payment=True`). Always read `effective_*` properties for current truth.
11. **Customer selection is always explicit:** never silently create-or-overwrite a `Customer` based on a typed phone/name at invoice-issue time.
12. **Status ("Tier") is always computed live, never stored on `Customer`:** call `tier_engine.evaluate_customer_status()` fresh, once per page load/Refresh (never per-row/per-repaint). *(The invoice-level `customer_status_snapshot` is a separate, immutable text snapshot of the label at issue time and does not change this rule.)*
13. **Responsive table call order:** `configure_responsive_table(table, columns)` **before** `setHorizontalHeaderLabels(...)`.
14. **NEW — Two dates, two jobs:** use **`Invoice.invoice_date`** (business/purchase date) for anything a person would call "the date of the sale" — filtering, grouping, sorting, display, tier periods, decay age, PDFs. Use **`created_at`** only for audit and for ordering events that need sub-day precision (due-payment chains). **Never override `created_at`.** Format `invoice_date` directly (`.strftime`) — never through `to_local_str`. When ordering by `invoice_date`, add a tiebreaker (`Invoice.id`).
15. **NEW — Snapshot, don't reference, for historical text:** `InvoiceItem.product_name` and `Invoice.customer_status_snapshot` are text snapshots; deleting/renaming a `Product` or changing a customer's Status must never alter existing invoices.
16. **NEW — Checkboxes:** use `theme.TickCheckBox`, not a plain `QCheckBox` with QSS indicator rules (Qt drops the native tick the moment `::indicator` is styled, and mixing bare declarations with selector blocks silently breaks the stylesheet).
17. **NEW — Admin-managed catalogs** (Customer Types, Status Tiers, Products) follow one pattern: Settings table + small `*Dialog`, case-insensitive duplicate check *outside* the session, delete confirmation *outside* the session, seed defaults in the migration (never re-seed), and consumer screens refresh on page switch rather than requiring a restart.

---

## 📦 Production Compiling (PyInstaller)
```bash
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="ChashiBondhuSuite" main.py
```
- `--onedir` (not `--onefile`) recommended for PyQt6 apps to avoid slow startup unpacking.
- `--add-data "assets;assets"` bundles the logo/icon/fonts folder.
- No SVG/image-plugin concerns for checkboxes: `TickCheckBox` is pure `QPainter`.

---

## ▶️ Suggested first steps for the next session
1. *(Done — owner confirmed migrations are applied through `j6k7l8m9n0o1`.)*
2. Smoke-test: add/edit/delete a Product in Settings → open Invoice Terminal → pick it → issue an invoice; issue a **backdated** invoice and confirm the PDF date, History Ledger date, Dashboard period, and customer Last Purchase all show the backdated day while `created_at` in the DB is "now".
3. Tick **Add Customer Status at Invoice** and confirm the PDF Bill-To shows it.
4. Upload → resize → save → Resize → Delete a signature; reissue a PDF with no signature.
5. *(Done — owner confirmed the `TickCheckBox` tick mark renders on all three checkboxes.)*
6. Decide on Known Open Item #1 (persist per-item unit) — it is the most visible functional gap left from the Product-catalog work.
