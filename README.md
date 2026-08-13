# Vermi-Compost Factory Management Suite

A professional Windows desktop application tailored for the automated tracking, operations management, invoice provisioning, and customer relationship management of a Vermi-composting factory. Built specifically to handle primary product lines (**Vermi-compost** and **Earthworms**), this application transitions legacy spreadsheet-based operations into a modern, highly secure database-driven transactional engine — complete with a searchable customer directory, purchase-history analytics, and a configurable purchase-volume-based customer loyalty ("Status") system.

---

## 🚀 Key Features

*   **Interactive Invoice Terminal (Decoupled MVC Layout):**
    *   Dual-panel transaction designer separating client details from transactional workflows.
    *   **Searchable customer picker** — type any part of a customer's name or phone number for live autocomplete; selecting one shows their phone, type, and current loyalty Status inline. An **"+ New"** inline panel registers a brand-new customer on the spot and auto-selects them, with zero context-switching away from the invoice.
    *   Live reactive cart management supporting dynamic item entry, volume/pricing multipliers, and row deletions.
    *   Configurable financial fields per invoice: flat **Discount**, user-entered **VAT %** (no fixed system tax), optional **Transport** charge (toggleable, only appears on the PDF when used), and a manual **Less Adjustment** deduction — computed in that exact order down to the Grand Total.
    *   Payment states: `Paid`, `Due`, `Partial Payment`, with an immutable-once-issued invoice model. Later payments toward a due balance are tracked as linked payment records rather than editing the original sale.
*   **Customer Management:** A dedicated Customers page with two views:
    *   **Customer Directory** — searchable list of every customer (name, phone, email, type, live Status badge), with quick Edit and "View Ledger" actions.
    *   **Purchase Summary** — a per-customer pivot: total invoices, grand total, discount, paid, due, last purchase date, and total kg sold per product — with an always-visible frozen totals row summarizing every customer at a glance.
*   **Configurable Customer Status (Loyalty Tiers):** Define your own tiers (e.g. Silver/Golden/Platinum) with their own qualifying purchase amount and evaluation period (monthly or yearly) — entirely from the Settings page, no code changes required. Status is computed live from real purchase history: customers **hold** an earned tier for an admin-configurable number of months, and a tier **gradually decays** if a customer's due balance goes unpaid past a configurable grace period.
*   **Operational Dashboard Analytics:** High-impact metric panels compiling revenue, compost/earthworm volumes sold (kg), and total invoices — scoped to Today, a specific Month/Year, a custom Date Range, or All Time — plus a live, unfiltered feed of the 10 most recent transactions.
*   **Sales History Ledger:** Full transaction history with a fast **Quick Search** (matches invoice ID, customer name, phone, date, status, or amount as you type — no button needed), plus dedicated Date Range and Status filters for more targeted queries. Jump straight to any customer's full invoice history in one click from the Customers page.
*   **Automated Document Exports:**
    *   **PDF Invoice Generation:** Pixel-perfect, print-ready records via `ReportLab`, including the company logo, itemized breakdown, and secure signature integration. Due-payment receipts get their own compact layout.
    *   **Excel & PDF Ledger Exports:** One "Export" button covering both formats, respecting whatever filter is currently active on the ledger.
*   **Operator Profiles & Secure Signatures:** Custom binary signature inputs — image uploads are automatically resized to a 200×80px bounding box and written into PostgreSQL as isolated byte-streams (`BYTEA`).
*   **Centralized, Responsive UI Theme:** A single `theme.py` module governs the app's entire look — colors, card styles, and how tables/buttons adapt to window resizing — so the whole app can be re-themed or re-tuned for responsiveness from one file.

---

## 🛠️ Tech Stack

*   **GUI Framework:** PyQt6 (Python 3.11 Target Execution Environment)
*   **Database Engine:** PostgreSQL
*   **ORM Integration:** SQLAlchemy Layer
*   **Migration Framework:** Alembic
*   **Document Generation Engines:** ReportLab (PDF) & openpyxl (Excel Data Matrices)
*   **Compilation Toolchain:** PyInstaller (.exe standalone packaging)

---

## 📂 Project Architecture

```text
vermi_sales_app/
│
├── alembic/                  # Database schema versions & migration histories
├── assets/                   # System runtime image matrices & program icons
│   ├── logo.png              # Formatted visual invoice logo asset
│   └── app_icon.ico          # Native Windows window execution icon
│
├── src/                      # Monolithic Python Source Modules
│   ├── config/                    # App-wide configuration
│   │   ├── company_config.py      # Client branding + invoice payment-status colors
│   │   ├── pdf_styles.py          # Per-section PDF background theming
│   │   └── theme.py               # UI chrome, responsive table/button helpers, Status badge palette
│   │
│   ├── database/              # Relational data wrappers
│   │   ├── connection.py      # Engine lifecycles & session context managers
│   │   └── models.py          # Declarative models (User, Customer, CustomerType, CustomerTier,
│   │                          #   AppSettings, Invoice, InvoiceItem)
│   │
│   ├── views/                 # Decoupled GUI display layers (PyQt6 Layouts)
│   │   ├── main_window.py         # Main navigation / sidebar
│   │   ├── dashboard_view.py      # Metric tiles & recent-activity feed
│   │   ├── invoice_view.py        # Split-pane interactive invoice terminal
│   │   ├── history_view.py        # Sales history ledger + filters
│   │   ├── customer_view.py       # Customer Directory + Purchase Summary
│   │   ├── settings_view.py       # Status tiers, customer types, Status rules
│   │   ├── due_payment_dialog.py  # Due-payment recording & payment-history dialogs
│   │   └── profile_view.py        # Signature management & identity configs
│   │
│   ├── controllers/           # Business logic intermediaries
│   │   ├── invoice_controller.py    # Live cart calculation & atomic sales handlers
│   │   ├── dashboard_controller.py  # KPI aggregation data queries
│   │   ├── history_controller.py    # Search/filter query engines
│   │   ├── customer_controller.py   # Customer CRUD + purchase-summary aggregation
│   │   ├── settings_controller.py   # Status tier / customer type / rules management
│   │   └── profile_controller.py    # Binary image transformations
│   │
│   └── utils/                 # Utility modules
│       ├── pdf_generator.py   # Structural PDF compilation scripts
│       ├── excel_exporter.py  # Financial spreadsheet generation tools
│       ├── tier_engine.py     # Live Customer Status computation (tiers, hold, decay)
│       └── time_utils.py      # UTC-stored / local-display timestamp helpers
│
├── .env                       # Application environment variables (Git Ignored)
├── alembic.ini                # Relational target configurations
├── requirements.txt           # Python ecosystem manifest
└── main.py                    # Central execution hook
```

---

## 💻 Environment Setup & Local Installation

### 1. System Requirements & Prerequisites
Ensure you have Python 3.11 and a live PostgreSQL instance up and running on your local machine.

### 2. Clone the Repository & Configure Python Space

```bash
# Move into target file directory
cd vermi_sales_app

# Create a clean isolated virtual environment
python -m venv venv

# Activate local environment configurations
# For Windows PowerShell:
.\venv\Scripts\Activate.ps1
# For standard Command Prompt:
.\venv\Scripts\activate.bat
```

### 3. Install Environment Requirements

```bash
pip install -r requirements.txt
```

### 4. Setup Local Environment Variables
Create a file named `.env` in the root repository directory and paste the following, adjusting credentials to match your PostgreSQL setup:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/vermi_factory_db
```

### 5. Execute Relational Migrations

```bash
# Initialize target data matrices
alembic upgrade head
```

This creates every table, including the newer `customer_types`, `customer_tiers`, and `app_settings` tables, and seeds sensible defaults (a starter set of customer types, three Status tiers, and default Status-rule values) that are fully editable afterward from the Settings page.

### 6. Boot the Application

```bash
python main.py
```

---

## ⚙️ Configuring Customer Status (Loyalty Tiers)

Out of the box, three example Status tiers are seeded (Silver / Golden / Platinum) — these are just a starting point and are meant to be adjusted to your actual business from the **Settings** page:

*   **Status Tiers** — add, edit, delete, or reorder any number of tiers, each with its own qualifying purchase amount and evaluation period (monthly or yearly).
*   **Customer Types** — a simple admin-managed list (e.g. Retail, Wholesale, Distributor) assignable per customer.
*   **Status Rules** — three values controlling how Status behaves over time:
    *   **Grace Period** — days a customer's due balance can go unpaid before any Status penalty starts.
    *   **Decay Step** — additional days per further Status downgrade after the grace period expires.
    *   **Status Hold Period** — months a customer keeps an earned Status level before it re-evaluates against current purchase activity.

Status is always computed live from actual invoice history — nothing is stored or needs to be recalculated/migrated after changing these settings; the next time any screen shows a customer's Status, it reflects the new rules immediately.

---

## 📦 Production Compiling Workflow (Generating .exe)

When you are ready to package the system for standalone client deployment, follow this specific process to bundle it using PyInstaller.

### 1. Preparation Check
Verify that your system asset paths are routing dynamically inside the execution wrapper using your asset path helper, which correctly switches lookup environments when checking for runtime folders inside `sys._MEIPASS`.

### 2. Run Compilation
Execute the following directly from the root of your application terminal workspace:

```bash
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="VermiCompostSuite" main.py
```

### 3. Output Location
Once the compiler completes its task successfully:

*   The raw working directories can be cleaned out from the `./build` folder.
*   Your production distribution package will be located entirely inside `./dist/VermiCompostSuite/`. You can copy or distribute this folder directly to any client workstation running Windows 10/11. The application boots cleanly via `VermiCompostSuite.exe`.

---

### 💡 Developer Notes

*   **High-DPI / text color:** if elements of the GUI present invisible placeholder fonts or light input fields inside specific dark desktop visual styles, check that explicit stylesheet elements have the correct text colors applied alongside background parameters (e.g., `background-color: #ffffff; color: #2c3e50;`).
*   **Theming & responsive behavior:** app-wide colors, card styles, table responsiveness (`theme.configure_responsive_table()`), and Customer Status badge colors (`theme.STATUS_TIER_PALETTE`) are all centralized in `src/config/theme.py`. Prefer extending that file over hardcoding style values in a view.
*   **Invoice immutability:** once an invoice is issued, its own stored fields are never edited — later payments against a due balance are recorded as new linked records instead. Always read a customer's or invoice's *effective* balance/status (e.g. `Invoice.effective_status`) rather than the raw stored field when displaying current truth.
