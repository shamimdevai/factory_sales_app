# Vermi-Composting Factory Invoice & Sales App (Project Specification & State)

> **Last updated:** 2026-08-01 — reflects the actual current, working state of the codebase. Start new chats by uploading this file plus the current project zip (or the specific files you're working on).

---

## 📌 Project Overview
A professional Windows desktop application for a vermi-composting factory (branded **Chashi-Bondhu**), selling **Vermi-compost** and **Earthworms**. Replaces manual Excel invoicing with a PyQt6 desktop app backed by PostgreSQL, with PDF/Excel export and digital signatures. It provides a secure UI for entering transaction data, tracks database records, computes dashboard statistics.

---

## 🛠️ Tech Stack
- **OS Platform:** Windows 10/11 (target deployment)
- **Language:** Python 3.11
- **UI Framework:** PyQt6 (`Fusion` style + explicit light `QPalette`, centrally themed via `src/config/theme.py`)
- **Database:** PostgreSQL + SQLAlchemy ORM
- **Migrations:** Alembic (currently at 5 revisions — see below)
- **Exports:** ReportLab (PDF), openpyxl (Excel)
- **Compiler:** PyInstaller (.exe bundling)
- **Env management:** python-dotenv (for local credential isolation)

---

## ✅ Current Feature State (verified working)

### Dashboard (`dashboard_view.py` + `dashboard_controller.py`)
- KPI tiles (Total Revenue, Compost kg, Worms kg, Total Invoices).
- **Period selector** (Row 1, light-blue tinted `QFrame`): dropdown **View:** `Today` (default) / `Month` (month name + year) / `Year` / `Date Range` (From/To) / `All`, plus a **🔍 View** button. Only the input(s) relevant to the selected mode are visible (e.g. Month shows month+year, Year shows year only). KPI tiles are recalculated and scoped to whichever period is selected; excludes due-payment records from the count/revenue math (see Due-Payment Chain section).
  - **"All"** mode shows a caption like `Showing: All Time (2026-07-18 to 2026-07-20)` — the actual earliest/latest invoice dates are queried live (`func.min`/`func.max` on `Invoice.created_at`, excluding due-payment records) rather than a generic "All Time" label. Falls back to `All Time (No records yet)` if there are no invoices at all.
- KPI cards (Row 2, light-gray tinted `QFrame`) show a small **"Showing: ..."** caption confirming the active period.
- **"Recent 10 Records"** table (8 columns: Invoice ID, Customer Name, Date, Items Count, Grand Total, Status, Due, Payment) is a global, **unfiltered** recent-activity feed — intentionally separate from the period selector above. Includes due-payment records inline (purple-tinted ID/Status, customer name wraps to a 2nd line as `(Due Payment for #X)`, Grand Total/Due show `—`, Payment shows the amount received in that specific transaction).
- Table columns are data-responsive: short/uniform columns use `ResizeToContents`; Customer Name/Status stay `Interactive` with word-wrap + `resizeRowsToContents()` so long text wraps onto extra lines instead of truncating or overflowing.
- Compost/Worms kg aggregation matches product names by keyword (`ILIKE '%compost%'` / `ILIKE '%worm%'`), joined to `Invoice` so date-period scoping and the due-payment exclusion apply correctly.

### Invoice Terminal (`invoice_view.py` + `invoice_controller.py`)
Financial fields, in calculation order:
```
taxable_amount = subtotal − discount
VAT_amount     = taxable_amount × VAT_rate
grand_total    = taxable_amount + VAT_amount + transport_charge − less_adjustment   (clamped ≥ 0)
due_amount     = grand_total − paid_amount                        (computed property, not stored)
```
- **Discount**: flat amount, user-entered per invoice, applied before VAT.
- **VAT** (renamed from "Tax"): user-entered percentage per invoice, default **0%**.
- **Transport** (new): optional flat add-on, applied after VAT, before Less Adjustment. Controlled by a **checkbox** (`chk_transport`, styled as a custom bordered toggle) — unchecked (default) keeps the amount field hidden and locked to `0.00`; checking it reveals `spin_transport` for entry. Only included in `grand_total` and only appears as its own PDF line when the checkbox was checked at issuing time (`show_transport_charge` flag, stored per-invoice, immutable after issuing). UI labels: **"Transport:"** (checkbox + totals display); PDF label: **"Transportation:"**.
- **Less Adjustment**: flat manual deduction applied after VAT (and after Transport), before grand total.
- **Payment Status** dropdown: `Paid`, `Due`, `Partial Payment`.
  - `Paid` → paid_amount = grand_total, due = 0
  - `Due` → paid_amount = 0, due = grand_total
  - `Partial Payment` → reveals a "Payment:" amount box; due = grand_total − paid (validated: must be > 0 and < grand_total)
- Status text and paid/due amounts are color-coded via `company_config.resolve_status_color()` (paid=green, due=red, partial=blue) — matches by substring so renaming the label text doesn't break the color logic. Shared by UI, History table, Dashboard table, and PDF.
- "Issue Invoice" button saves the sale. "Download PDF" button, enabled after issuing, saves that invoice's PDF on demand.
- Metrics box uses `QGridLayout` (fixed-shape, 2 rows) for the billing row (Discount/VAT + Transport/Less Adj), totals row (Subtotal/Discount/VAT + Transport/Less Adj/Grand Total), and payment row — never extends sideways indefinitely. Action buttons live on their own row.
- Cart items table uses fixed column widths with native scrollbars.
- **Known bug fixed:** `commit_invoice`'s `Invoice(...)` constructor call had a stray line-break/indentation glitch on the `grand_total=grand_total, paid_amount=paid_amount,` line (harmless whitespace-only issue once corrected, but was worth flagging — always re-view a file before editing it if unsure of its exact current state).

### Due-Payment Chain (new feature — spans `models.py`, `invoice_controller.py`, `history_view.py`/`history_controller.py`, `due_payment_dialog.py`, `pdf_generator.py`)
Once an invoice is issued it's **immutable** — no edit, no reopening, ever. `Paid` invoices are final. For `Due`/`Partial Payment` invoices, the customer's later payments toward that balance are now tracked as **linked due-payment records** rather than requiring a fake product sale:

- **DB model**: `Invoice` gained `parent_invoice_id` (self-referencing FK, always points to the ORIGINAL root invoice, never to an intermediate due-payment — keeps balance math a flat sum instead of tree recursion) and `is_due_payment` (Boolean). A due-payment record has `total_amount/discount/tax/less_adjustment/transport_charge = 0`, `grand_total = 0`, `paid_amount = amount received`, `payment_status = "Paid"` (the transaction itself is complete).
- **Computed properties on `Invoice`** (dynamic, never overwrite the original stored fields):
  - `effective_paid_amount` = own `paid_amount` + sum of all linked due-payments' `paid_amount`
  - `effective_due_amount` = `grand_total − effective_paid_amount`
  - `effective_status` = `"Paid"` if due ≤ 0, else `"Partial Payment"` if any payment recorded, else the original stored `payment_status`
- **`InvoiceController.record_due_payment(root_invoice_id, amount)`**: validates amount is `>0` and `≤` current due (0.01 float-safety tolerance), creates the linked record. Raises `ValueError` with a user-facing message on invalid input.
- **History Ledger** (`Actions` column): 📄 PDF (always) + 💰 **Pay Due** (shown only when `effective_due_amount > 0`, opens `DuePaymentDialog` to collect the amount, then offers to save a PDF receipt) + 🧾 **History** (shown only when the invoice has ≥1 linked due-payment, opens `PaymentHistoryDialog` listing the full chain with per-record PDF reprint).
- Due-payment records are **hidden from the main History Ledger table** (only root/original sale invoices get their own row) — accessible only via the 🧾 History dialog on their root invoice. Dashboard's "Recent 10 Records" is the one place they DO show up inline (see Dashboard section).
- **PDF receipts**: a due-payment gets its own short "PAYMENT RECEIPT" layout (`pdf_generator.py::_build_due_payment_pdf`) stating it's a payment against Invoice #X's due balance, with Original Grand Total / Previously Paid / Paid Now / Remaining Due breakdown, and the date of that specific payment. The **root invoice's own PDF** (reprinted any time) shows *effective* (not stale as-issued) Amount Paid/Balance Due/Status, plus a small note listing linked due-payment IDs and the date of the most recent one if any exist.

### Sales History Ledger (`history_view.py` / `history_controller.py`)
- **"Filter By"** dropdown: `Date Range` (default, shows Start/End date pickers) / `Invoice ID` (partial numeric match) / `Customer Name` (case-insensitive partial match) / `Status` (`Paid`/`Due`/`Partial Payment` — filtered in Python since `effective_status` is a computed property, not a DB column). Only the relevant input(s) show for the selected mode. **🔍 Search** button replaces the old "Filter" button, with validation requiring non-empty text for Invoice ID/Customer Name modes.
- Table columns: Invoice ID, Customer, Date, Discount, Grand Total, **Status** (color-coded, effective), **Due** (effective), Actions (📄/💰/🧾 — see Due-Payment Chain).
- Excel export and Summary PDF export both reuse whatever filter is currently active (not just date range), via `_get_filtered_records()`.
- Fixed/interactive column widths with native scrollbars.

### Database (`models.py`)
`Invoice` fields: `total_amount` (subtotal), `discount_amount`, `tax_rate` (VAT), `less_adjustment`, `transport_charge`, `show_transport_charge`, `grand_total`, `paid_amount`, `payment_status`, `parent_invoice_id`, `is_due_payment`, `created_at` (naive UTC), plus computed properties `due_amount`, `effective_paid_amount`, `effective_due_amount`, `effective_status` (see Due-Payment Chain section).

**Migrations (run `alembic upgrade head` — `init_db()` alone won't add columns to an existing table):**
1. `8f6a5632b5e4` — initial schema
2. `c4d8f2a91b6e` — adds `discount_amount`, `paid_amount`
3. `d7f3a2c8b915` — adds `less_adjustment`
4. `e2a9c1f74d38` — adds `parent_invoice_id`, `is_due_payment` (due-payment chain)
5. `f7c3d81a2e56` — adds `transport_charge`, `show_transport_charge`

### PDF Invoice Engine (`pdf_generator.py`)
- Header includes the company logo (`cfg.COMPANY_LOGO_PATH`, drawn if the file exists).
- Two layouts, dispatched by `generate_invoice_pdf(invoice_id, path)` checking `invoice.is_due_payment`:
  - **`_build_sale_invoice_pdf`**: normal product-sale invoice. Financial block, in order: Subtotal → Discount → VAT → **Transportation** (only if `show_transport_charge` was checked at issuing) → Less Adjustment → Grand Total → Amount Paid → Balance Due (all *effective* figures, not stale as-issued). Two highlighted separator lines: above Subtotal, above Grand Total. The `TableStyle` row-index math for these separators is **computed dynamically** (`num_summary_rows = 8 if show_transport_charge else 7`) rather than hardcoded, since the optional Transportation row shifts everything by one.
  - **`_build_due_payment_pdf`**: short "PAYMENT RECEIPT" layout for due-payment records — see Due-Payment Chain section.
- Fixed footer on every page: WhatsApp / Website / Facebook, pulled from `company_config.py`.
- Section backgrounds are theme-driven via `src/config/pdf_styles.py` (per-section hex + alpha) — **note:** this is the PDF-specific theme file, separate from the new app-UI `src/config/theme.py`.
- **Bengali `৳` glyph fix**: only the currency symbol is wrapped in `<font face="UnicodeFont">৳</font>` inline markup — never globally override `styles['Normal'].fontName` (breaks English labels).
- Dates shown in local time throughout.

### Timezone fix (`src/utils/time_utils.py`)
`created_at` stored as naive UTC, displayed via `to_local_str(dt)` (fixed +6h offset) everywhere a timestamp is shown: PDF invoice date, History Ledger, Dashboard, due-payment receipts, "All Time" range caption.

### White-labeling (`src/config/company_config.py`)
Client branding only: name, address, email, phone, WhatsApp, website, Facebook, currency symbol, logo/app-icon paths, `STATUS_COLORS`/`resolve_status_color()`. **Deliberately does NOT include general UI chrome colors anymore** — those moved to `theme.py` (see below).

### 🎨 Centralized UI Theme (`src/config/theme.py` — new file)
Single source of truth for **app look-and-feel**, separate from `company_config.py` (client branding):
- Constants: `PAGE_BACKGROUND` (`#EEF6F0`, subtle mint-green tint used app-wide), `SIDEBAR_BACKGROUND` (`#2C3E50`, kept navy per client preference), `SIDEBAR_HOVER`, `CARD_BACKGROUND` (`#FFFFFF`), `BORDER_COLOR` (`#CBD5E1`), `ACCENT`/`ACCENT_DARK` (`#1ABC9C`/`#16A085`), `TEXT_PRIMARY`, `TEXT_MUTED`.
- Helper functions: `card_frame_style()` (standard white bordered card), `input_style(widget_selector)` (bordered input field — **auto-appends `combobox_dropdown_style()` whenever `"QComboBox"` appears in the selector**, so every combobox in the app gets working hover/selection text color by default without each caller remembering to bolt it on separately — this was the root cause of a white-on-white dropdown-hover bug found on the Dashboard period selector), `combobox_dropdown_style()`.
- Applied to: `main.py` (app-wide `QPalette` + safety-net stylesheet), `main_window.py` (sidebar, stacked widget, scroll-area backgrounds), and the cross-cutting card/border/accent colors in `dashboard_view.py`, `history_view.py`, `invoice_view.py`, `profile_view.py`, `due_payment_dialog.py`. One-off semantic button colors (red delete, blue info-buttons, purple due-payment-chain accents) were deliberately left as local literals — centralizing genuinely single-use colors wasn't worth the added indirection.
- To re-theme the whole app: edit `theme.py` only.

### Responsiveness (`main_window.py` + all table-bearing views)
- Dynamic minimum window size (25% of screen's available width/height, 480×400 floor).
- Every page wrapped in a `QScrollArea` (`ScrollBarAsNeeded` both axes).
- All data tables (Invoice cart, History ledger, Dashboard recent-records) use fixed/interactive/ResizeToContents column widths instead of blanket `Stretch`.
- Invoice Terminal metrics box: `QGridLayout`, fixed shape.
- **Known bug fixed:** an earlier edit accidentally deleted the `def _apply_dynamic_minimum_size(self):` line itself while leaving its docstring behind as an orphaned no-op statement inside `__init__` — syntactically valid Python (so it didn't error at parse time) but would have crashed at runtime since the method no longer existed. Caught and fixed; worth double-checking method definitions survive edits, not just docstrings/bodies.

### UI/UX fixes applied
- Invisible label bug (white-on-white under Windows Dark Mode + Fusion style) — fixed via explicit light `QPalette` + `QLabel` stylesheet safety net in `main.py`.
- Dropdown hover text invisible — fixed via `theme.combobox_dropdown_style()`, now auto-applied by `theme.input_style()` (see Centralized UI Theme section).
- Windows taskbar/app icon wired via `cfg.APP_ICON_PATH`.
- Removed dead code: `sales_view.py` / `sales_controller.py` (duplicate, unused invoice screen).
- Fixed duplicate `QApplication` instantiation in `main.py`.
- Fixed missing `Qt` import in `profile_controller.py`.

---

## 🐛 Known Open Items

1. Older invoices created before the `Paid/Unpaid/Partial` → `Paid/Due/Partial Due` → `Paid/Due/Partial Payment` renames still display their original saved status text — this is correct historical record-keeping, not a bug.
2. **Native Windows title bar coloring was explored and explicitly dropped** — the DWM API approach only works on Windows 11 (build 22000+), not Windows 10, so the app-wide mint-green `PAGE_BACKGROUND` theme was used instead as an OS-independent way to make the app visually distinct. No title-bar-coloring code remains in `main.py`.
3. `assets/fonts/NotoSansBengali-*.ttf` were intentionally removed from the working zip to keep it small (confirmed fine — falls back to Windows' `Nirmala.ttf` at runtime; only matters for PyInstaller bundling later).

None else currently outstanding.

---

## 📂 Current Project Directory
```text
factory_sales_app/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 8f6a5632b5e4_initial_schema_setup.py
│       ├── c4d8f2a91b6e_add_discount_and_paid_amount.py
│       ├── d7f3a2c8b915_add_less_adjustment.py
│       ├── e2a9c1f74d38_add_due_payment_chain.py
│       └── f7c3d81a2e56_add_transport_charge.py
├── assets/
│   ├── app_icon.ico
│   └── logo.png
├── src/
│   ├── config/
│   │   ├── company_config.py   # Client branding + status colors
│   │   ├── pdf_styles.py       # Per-section PDF background theming
│   │   └── theme.py            # NEW — app-wide UI chrome colors (background/card/border/accent)
│   ├── controllers/
│   │   ├── dashboard_controller.py
│   │   ├── history_controller.py
│   │   ├── invoice_controller.py
│   │   └── profile_controller.py
│   ├── database/
│   │   ├── base_class.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── utils/
│   │   ├── asset_utils.py
│   │   ├── excel_exporter.py
│   │   ├── pdf_fonts.py
│   │   ├── pdf_generator.py
│   │   └── time_utils.py
│   └── views/
│       ├── dashboard_view.py
│       ├── due_payment_dialog.py   # NEW — DuePaymentDialog + PaymentHistoryDialog
│       ├── history_view.py
│       ├── invoice_view.py
│       ├── main_window.py
│       └── profile_view.py
├── .env
├── alembic.ini
├── requirements.txt
└── main.py
```

---

## 🎯 Global Development Rules (unchanged, +2 new)
1. **Strict Decoupling:** Views = GUI only. Business logic lives in Controllers/Utils.
2. **Robust Error Handling:** DB/file/image ops wrapped in `try/except` with `QMessageBox` feedback.
3. **Clean DB Sessions:** context managers / `try-finally`, no dangling connections.
4. **Signature Storage:** signatures resized to max 200×80px PNG, stored as `BYTEA`, never as file paths.
5. **Asset Path Resolution:** always via `src/utils/asset_utils.py::get_asset_path()`.
6. **White-labeling:** all client-specific branding goes in `src/config/company_config.py` / `src/config/pdf_styles.py` — never hardcode in views/controllers/utils.
7. **PDF fonts:** never globally override `styles['Normal'].fontName` with a script-specific font — wrap only the specific glyphs that need it in inline `<font face="...">` markup.
8. **Responsive layouts:** avoid open-ended `QHBoxLayout` rows for anything that can grow — use `QGridLayout` with a fixed shape, or wrap in a scroll area.
9. **NEW — App-wide UI theming:** all background/card/border/accent colors go through `src/config/theme.py` (`theme.card_frame_style()`, `theme.input_style()`, `theme.combobox_dropdown_style()`, or the raw constants) — never hardcode `#cbd5e1`/`white`/`#1abc9c` etc. directly in a view. Semantic one-off button colors (success/danger/info-blue/purple-chain) are fine as local literals.
10. **NEW — Invoice immutability + due-payment chain:** once issued, an invoice's own stored fields (`paid_amount`, `payment_status`, etc.) are **never edited**. Later payments toward an outstanding balance are recorded as new linked `Invoice` rows (`is_due_payment=True`, `parent_invoice_id` pointing to the root). Always read/display `effective_*` properties for current truth, not the raw stored fields, anywhere a balance or status is shown to the user.

---

## 📦 Production Compiling (PyInstaller)
```bash
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="ChashiBondhuSuite" main.py
```
- `--onedir` (not `--onefile`) recommended for PyQt6 apps to avoid slow startup unpacking.
- `--add-data "assets;assets"` bundles the logo/icon/fonts folder into the `.exe`.
