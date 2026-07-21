# Vermi-Composting Factory Invoice & Sales App (Project Specification & State)

> **Last updated:** 2026-07-19 — reflects the actual current, working state of the codebase. Start new chats by uploading this file plus the current project zip (or the specific files you're working on).

---

## 📌 Project Overview
A professional Windows desktop application for a vermi-composting factory (branded **Chashi-Bondhu**), selling **Vermi-compost** and **Earthworms**. Replaces manual Excel invoicing with a PyQt6 desktop app backed by PostgreSQL, with PDF/Excel export and digital signatures. It provides a secure UI for entering transaction data, tracks database records, computes dashboard statistics.

---

## 🛠️ Tech Stack
- **OS Platform:** Windows 10/11 (target deployment)
- **Language:** Python 3.11
- **UI Framework:** PyQt6 (`Fusion` style + explicit light `QPalette`)
- **Database:** PostgreSQL + SQLAlchemy ORM
- **Migrations:** Alembic (currently at 3 revisions — see below)
- **Exports:** ReportLab (PDF), openpyxl (Excel)
- **Compiler:** PyInstaller (.exe bundling)
- **Env management:** python-dotenv (for local credential isolation)

---

## ✅ Current Feature State (verified working)

### Dashboard
- Wired into `main_window.py`. KPI tiles (revenue, compost kg, worms kg, invoice count) + recent-5 table.
- Compost/Worms kg aggregation bug fixed: matches product names by keyword (`ILIKE '%compost%'` / `ILIKE '%worm%'`) instead of an exact-string match that never matched real product names (was always showing 0.00 kg).
- Table dates now shown in local time (see Timezone section below).

### Invoice Terminal (`invoice_view.py` + `invoice_controller.py`)
Financial fields, in calculation order:
```
taxable_amount = subtotal − discount
VAT_amount     = taxable_amount × VAT_rate
grand_total    = taxable_amount + VAT_amount − less_adjustment   (clamped ≥ 0)
due_amount     = grand_total − paid_amount                        (computed property, not stored)
```
- **Discount**: flat amount, user-entered per invoice, applied before VAT.
- **VAT** (renamed from "Tax"): user-entered percentage per invoice, default **0%**.
- **Less Adjustment**: flat manual deduction applied after VAT, before grand total.
- **Payment Status** dropdown: `Paid`, `Due`, `Partial Payment` (renamed from `Paid/Unpaid/Partial`, then `Paid/Due/Partial Due`).
  - `Paid` → paid_amount = grand_total, due = 0
  - `Due` → paid_amount = 0, due = grand_total
  - `Partial Payment` → reveals a "Payment:" amount box; due = grand_total − paid (validated: must be > 0 and < grand_total)
- Status text and paid/due amounts are color-coded via `company_config.resolve_status_color()` (paid=green, due=red, partial=blue) — matches by substring (`"partial" in status.lower()`, etc.) so renaming the label text doesn't break the color logic. Shared by UI, History table, and PDF.
- "Issue Invoice" button (renamed from "Issue & Print Invoice") saves the sale. "Download PDF" button, enabled after issuing, saves that invoice's PDF on demand.
- **Layout is now fully responsive**: the metrics box uses `QGridLayout` (not `QHBoxLayout`) for the billing row, totals row, and payment row, so it always wraps onto a fixed number of rows instead of extending sideways indefinitely and pushing buttons off-screen on narrow windows. Buttons live on their own row so they're never unreachable.
- Cart items table uses fixed column widths (not force-stretch) with native scrollbars.

### Database (`models.py`)
`Invoice` fields: `total_amount` (subtotal), `discount_amount`, `tax_rate` (VAT), `less_adjustment`, `grand_total`, `paid_amount`, `payment_status`, `created_at` (naive UTC), plus computed property `due_amount = grand_total − paid_amount`.

**Migrations (run `alembic upgrade head` — `init_db()` alone won't add columns to an existing table):**
1. `8f6a5632b5e4` — initial schema
2. `c4d8f2a91b6e` — adds `discount_amount`, `paid_amount`
3. `d7f3a2c8b915` — adds `less_adjustment`

### Sales History Ledger (`history_view.py` / `history_controller.py`)
- Table columns: Invoice ID, Customer, Date, Discount, Grand Total, **Status** (color-coded), Due, Actions (reprint PDF).
- Excel export and Summary PDF export both include Discount, Grand Total, and Due columns + totals row.
- Fixed column widths (not force-stretch) with native scrollbars, so narrow windows get a horizontal scrollbar instead of truncated columns (e.g., Date was getting cut off before this fix).

### PDF Invoice Engine (`pdf_generator.py`)
- Header includes the company logo (`cfg.COMPANY_LOGO_PATH`, drawn if the file exists).
- Financial block, in order: Subtotal → Discount → VAT → Less Adjustment → Grand Total → Amount Paid → Balance Due, color-coded (paid=green, due=red). Two highlighted (darker, thicker) separator lines: above Subtotal, and above Grand Total.
- Fixed footer on every page: WhatsApp / Website / Facebook, pulled from `company_config.py`.
- Section backgrounds are theme-driven via `src/config/pdf_styles.py` (per-section hex + alpha).
- **Bengali `৳` glyph fix**: ReportLab's default Helvetica font has no Bengali glyphs, so the currency symbol printed as a missing-glyph box. Fixed via `src/utils/pdf_fonts.py::register_unicode_fonts()`, which registers a Unicode font (bundled `assets/fonts/NotoSansBengali-*.ttf`, or falls back to Windows' built-in `Nirmala.ttf`). **Important implementation detail:** only the currency symbol itself is wrapped in `<font face="UnicodeFont">৳</font>` inline markup (via a local `sym` variable built once per PDF function) — the rest of each Paragraph stays in default Helvetica. Do **not** globally override `styles['Normal'].fontName`, since Bengali-only fonts typically lack full Latin glyph coverage and doing so blanks out all English labels (this was tried and reverted after breaking every English label on the invoice).
- Dates now shown in local time (see Timezone section below).

### Timezone fix (`src/utils/time_utils.py`)
`created_at` is stored as naive UTC (`datetime.utcnow()`) — correct for storage, but was being displayed as-is, showing times 6 hours behind actual Bangladesh time. Fixed via `to_local_str(dt)` (fixed +6h offset, no external tz dependency), applied everywhere a timestamp is displayed: PDF invoice date, History Ledger date column, Dashboard recent-sales date column.

### White-labeling (`src/config/company_config.py`)
Single file to re-brand for a new client: name, address, email, phone, WhatsApp, website, Facebook, currency symbol, logo path (`assets/logo.png`), app icon path (`assets/app_icon.ico`), and `STATUS_COLORS` / `resolve_status_color()`. Resolved via `src/utils/asset_utils.py::get_asset_path()` (dev + PyInstaller `.exe`-safe).

### Responsiveness (`main_window.py` + all table-bearing views)
- **Dynamic minimum window size**: `_apply_dynamic_minimum_size()` sets the minimum to 25% of the actual screen's available width/height (via `QGuiApplication.primaryScreen()`), not a fixed pixel value — so it scales correctly on any monitor, with a 480×400 floor.
- **Every page wrapped in a `QScrollArea`** with explicit `ScrollBarAsNeeded` policy on both axes, so any page that doesn't fit the window gets scrollbars instead of clipped/unreachable content.
- **All 3 data tables** (Invoice cart, History ledger, Dashboard recent-sales) use fixed/interactive column widths instead of blanket `Stretch` resize mode, so columns keep readable widths and a horizontal scrollbar appears on overflow instead of text getting squeezed unreadable.
- **Invoice Terminal metrics box** rebuilt with `QGridLayout` (billing row, totals row, payment row each capped at a fixed layout shape) instead of ever-extending `QHBoxLayout` rows — action buttons are on their own row so they can never be pushed off-screen.

### UI/UX fixes applied
- Invisible label bug (white-on-white under Windows Dark Mode + Fusion style) — fixed via explicit light `QPalette` + `QLabel` stylesheet safety net in `main.py`.
- Dropdown hover text invisible — fixed via explicit `QComboBox QAbstractItemView` styling.
- Windows taskbar/app icon wired via `cfg.APP_ICON_PATH`.
- Removed dead code: `sales_view.py` / `sales_controller.py` (duplicate, unused invoice screen).
- Fixed duplicate `QApplication` instantiation in `main.py`.
- Fixed missing `Qt` import in `profile_controller.py` (was crashing signature upload).

---

## 🐛 Known Open Items

1. Older invoices created before the `Paid/Unpaid/Partial` → `Paid/Due/Partial Due` → `Paid/Due/Partial Payment` renames still display their original saved status text — this is correct historical record-keeping, not a bug, and doesn't need fixing.

None currently outstanding beyond the above — `assets/logo.png` and `assets/fonts/NotoSansBengali-Regular.ttf` / `-Bold.ttf` are confirmed present in the project folder as of this update.

---

## 📂 Current Project Directory
```text
vermi_sales_app/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 8f6a5632b5e4_initial_schema_setup.py
│       ├── c4d8f2a91b6e_add_discount_and_paid_amount.py
│       └── d7f3a2c8b915_add_less_adjustment.py
├── assets/
│   ├── app_icon.ico
│   ├── logo.png
│   └── fonts/
│       ├── NotoSansBengali-Regular.ttf
│       └── NotoSansBengali-Bold.ttf
├── src/
│   ├── config/
│   │   ├── company_config.py   # White-label branding + status colors
│   │   └── pdf_styles.py       # Per-section PDF background theming
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
│   │   ├── asset_utils.py      # get_asset_path() — dev/.exe-safe
│   │   ├── excel_exporter.py
│   │   ├── pdf_fonts.py        # Unicode/Bengali font registration for ReportLab
│   │   ├── pdf_generator.py
│   │   └── time_utils.py       # UTC → local (Bangladesh, UTC+6) display conversion
│   └── views/
│       ├── dashboard_view.py
│       ├── history_view.py
│       ├── invoice_view.py
│       ├── main_window.py
│       └── profile_view.py
├── .env
├── alembic.ini
├── requirements.txt           # UTF-8 (was UTF-16, fixed)
└── main.py
```

---

## 🎯 Global Development Rules (unchanged)
1. **Strict Decoupling:** Views = GUI only. Business logic lives in Controllers/Utils.
2. **Robust Error Handling:** DB/file/image ops wrapped in `try/except` with `QMessageBox` feedback.
3. **Clean DB Sessions:** context managers / `try-finally`, no dangling connections.
4. **Signature Storage:** signatures resized to max 200×80px PNG, stored as `BYTEA`, never as file paths.
5. **Asset Path Resolution:** always via `src/utils/asset_utils.py::get_asset_path()`.
6. **White-labeling:** all client-specific branding goes in `src/config/company_config.py` / `src/config/pdf_styles.py` — never hardcode in views/controllers/utils.
7. **PDF fonts:** never globally override `styles['Normal'].fontName` with a script-specific font (e.g. Bengali-only) — wrap only the specific glyphs that need it in inline `<font face="...">` markup, or English text disappears. See PDF Invoice Engine section above.
8. **Responsive layouts:** avoid open-ended `QHBoxLayout` rows for anything that can grow (metrics, action bars) — use `QGridLayout` with a fixed shape, or wrap in a scroll area, so narrow windows never push content unreachably off-screen.

---

## 📦 Production Compiling (PyInstaller)
```bash
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="ChashiBondhuSuite" main.py
```
- `--onedir` (not `--onefile`) recommended for PyQt6 apps to avoid slow startup unpacking.
- `--add-data "assets;assets"` bundles the logo/icon/fonts folder into the `.exe`.
