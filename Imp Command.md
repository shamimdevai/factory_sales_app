# Vermi-Composting Factory Invoice & Sales App (Project Specification & State)



## 📋 Comprehensive System Requirements
1. **Database Migration (`alembic`):** Must support auto-generation of migrations based on SQLAlchemy models[cite: 13].
2. **Dashboard View:** Visual tiles displaying Key Performance Indicators (KPIs)[cite: 13]:
   - Total Sales Revenue (Current Month/Lifetime)[cite: 13]
   - Total Volume of Vermi-compost Sold (kg)[cite: 13]
   - Total Quantity of Earthworms Sold (kg)[cite: 13]
   - A tabular list of the 5 most recent sales transactions[cite: 13].
3. **Interactive Invoice Terminal (Option B Configuration):**
   - Left-column layout for tracking structured Customer Details and adding Products[cite: 13].
   - Right-column layout containing a dynamic live Cart Items grid with item line deletions[cite: 13].
   - Embedded input selectors for Payment Status (`Paid`, `Unpaid`, `Partial`)[cite: 13].
   - Automatic calculations for Subtotal, static 5% Tax, and Net Grand Total amounts[cite: 13].
4. **PDF Invoice Engine:**
   - Emits a clean, professional, styled single-page printable PDF layout[cite: 13].
   - Embeds the logged-in user's profile metadata and digital signature (stored in PostgreSQL DB as BYTEA)[cite: 13].
   - Renders transactional details in an aligned tabular form[cite: 13].
5. **Historical Sales Records & Filtering:**
   - Data grid view containing all completed transactions[cite: 13].
   - Date range filters (Start Date to End Date)[cite: 13].
   - **Excel Export:** Creates a beautifully formatted workbook with styled headers, correct data-type formatting, and dynamic sum total rows using formulas[cite: 13].
   - **PDF Ledger Report:** Creates a clean multi-page summary PDF of filtered records[cite: 13].
6. **User Profile & Signature Configuration:**
   - Allows users to change registration fields[cite: 13].
   - Signature upload window supporting PNG/JPG formats, which automatically flattens, resizes, and saves into the database binary column[cite: 13].
7. **Production Compiling:** Detailed workflow to bundle asset binaries, PyQt6 libraries, and native PostgreSQL drivers into a single, clean `.exe` using PyInstaller.

---


---

## 🎯 Global Development Rules
1. **Strict Decoupling:** Views (`src/views/`) must contain only GUI styling, layouts, and input signals. Business operations, data transformations, and database transactions must live inside Controllers or Utility modules.
2. **Robust Error Handling:** All database connections, file writes, and image operations must use clear `try/except` blocks with error prompts popping up in the UI (e.g., `QMessageBox`).
3. **Clean Database Sessions:** Sessions must be safely opened and closed using context managers or standard `try-finally` blocks to prevent memory leaks and dangling connection locks on PostgreSQL.
4. **Signature Storage:** Digital signatures must be processed cleanly. Do not store absolute paths. Convert uploaded images to a standard resolution (e.g., maximum 200x80px PNG), transform them to binary data (`bytes`), store them in the `BYTEA` PostgreSQL column, and reconstruct them temporarily in memory during invoice compilation.
5. **Dynamic Compile-time Asset Path Resolution:** Internal application files (like logo templates or system assets) must resolve paths cleanly inside the runtime environment whether it runs in raw python context or isolated PyInstaller containers via a custom utility function:
```text
import sys
import os

def get_asset_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
```
---

## 🚀 Independent Phase Execution Prompts
Below are highly detailed, self-contained prompts designed to be executed step-by-step in separate AI sessions to avoid context truncation or token limits.

### [PROMPT 1] Core Database Setup, Models, and Alembic Configuration
Copy and paste this prompt to your next AI assistant to construct the database tier.
```text
Role: Principal Database Engineer & Python Expert.
Objective: Build the Database layer for a PyQt6 desktop app. 
Files to create/configure:
1. `src/database/connection.py` - Setup a connection engine using SQLAlchemy with safety pools and standard Session context managers.
2. `src/database/models.py` - Define 4 relational tables using SQLAlchemy ORM:
   - `User`: id, name, username, email, password_hash, digital_signature (BYTEA), created_at.
   - `Customer`: id, name, phone (unique index), email, address, created_at.
   - `Invoice`: id, customer_id, user_id (who created it), total_amount, tax_rate, grand_total, payment_status, created_at.
   - `InvoiceItem`: id, invoice_id, product_name (Vermi-compost or Earthworms), quantity (numeric/float), unit_price, subtotal.
3. Show how to modify `alembic.ini` and `alembic/env.py` (including pulling DATABASE_URL from .env using dotenv) so "alembic revision --autogenerate" registers these tables correctly.
Provide fully implemented code, robust error handling, and clean SQL mapping structures.
```

### [PROMPT 2] Core MVC Controller and UI Layout Setup (Main Shell & Dashboard)
Copy and paste this prompt to build the visual shell.
```text
Role: Senior PyQt6 GUI Architect & Desktop App Developer.
Objective: Implement the main application container and Dashboard screen.
Context: You have SQLAlchemy models available in `src.database.models`.
Files to create/implement:
1. `src/views/main_window.py` - A responsive MainWindow layout featuring a left sidebar with vertical navigation tabs (Dashboard, New Sale, History, Profile) and a central StackedWidget to toggle screens.
2. `src/views/dashboard_view.py` - The KPI analytics screen containing:
   - High-contrast visual metric tiles (Total Monthly Revenue, Total Compost Weight, Total Earthworms, Total Invoices).
   - A tabular record list tracking the 'Recent 5 Sales'.
3. `src/controllers/dashboard_controller.py` - Logic mapping SQLAlchemy queries to populate the UI view dynamically upon loading. Include error boundaries.
Provide clean, professional styles, layouts, and data integration.
```

### [PROMPT 3] Invoice Creation Form, Validation, and Client Matching UI
Copy and paste this prompt to build the data entry system.
```text
Role: Desktop GUI Specialist.
Objective: Create the New Sale UI View and Business Logic Controller.
Context: You have a PostgreSQL database with Customer, Invoice, and InvoiceItem models.
Files to create/implement:
1. `src/views/sales_view.py` - A functional, validated data entry form containing:
   - Customer Section: Name, Phone (triggers auto-lookup), Email, Billing Address.
   - Sales Items: Dynamic line items where a user selects a product (dropdown), inputs quantities, and unit price. Must compute item subtotals dynamically and feature "Add Item" and "Delete Item" actions.
   - Bottom summary display (Calculates Total, Tax % and Grand Total).
   - A "Confirm Sale" and "Generate PDF" action trigger.
2. `src/controllers/sales_controller.py` - Controller logic that:
   - Queries existing customers by Phone as the user types; fills their record if matched.
   - Implements validation (no zero/negative inputs, completed fields).
   - Performs a transactional save: commits customer first (if new), writes the Invoice and all InvoiceItems inside a secure DB transaction block, and outputs the result.
Ensure robust UX validation and database integrity.
```

### [PROMPT 4] Multi-format Ledger Exporter (ReportLab PDFs & Styled openpyxl Sheets)
Copy and paste this prompt to create the reporting modules.
```text
Role: Technical Document Automation Engineer.
Objective: Write powerful, highly-styled document generators for PDFs and Excel sheets.
Files to create/implement:
1. `src/utils/pdf_generator.py` - A ReportLab generation module that produces:
   - A modern corporate single-page invoice including header logo, billing info, itemized grid table with alternate row colors, signature block embedding the raw byte-stream signature from PostgreSQL, and terms of service.
   - A multi-page summary report PDF compiling a ledger of sales records.
2. `src/utils/excel_exporter.py` - An openpyxl module that takes database-derived dict arrays and constructs an immaculate, professionally formatted spreadsheet:
   - Colored header rows, auto-fitted column widths, currency masks, borders, and a calculated bottom Total row using actual Excel formulas (`=SUM(...)`).
Provide clean, production-ready, bulletproof file IO code.
```

### [PROMPT 5] Complete Sales History View & Profile/Signature Configuration
Copy and paste this prompt to complete the application utilities.
```text
Role: Professional PyQt6 desktop app UI developer.
Objective: Build the Sales History Ledger and User Settings Panel.
Files to create/implement:
1. `src/views/history_view.py` & Controller - A search engine GUI with Date Range Pickers (Start/End Date). Runs queries to display sales records. Includes active action links to re-export single PDFs, mass export to Excel, or mass export summary PDFs.
2. `src/views/profile_view.py` & `src/controllers/profile_controller.py` - Form showing current operator metadata. Includes an "Upload Signature" button, letting users browse local files. It must process, scale down to 200x80px, convert to a standard PNG byte stream, and update the raw BYTEA user signature row in PostgreSQL.
Provide full functional layouts with intuitive workflows.
```

### [PROMPT 6] Application Assembly, Config, and PyInstaller Production Compiling
Copy and paste this prompt when you are ready to ship the software.
```text
Role: Windows DevOps & Application Packaging Engineer.
Objective: Construct the build script to compile the application into a standalone Windows .exe.
Files to create/actions to explain:
1. Create `main.py` - The central application pipeline executing the PyQt6 QApplication, establishing database handshakes, performing automatic migration sanity checks, and displaying the MainWindow shell.
2. Write a professional step-by-step instruction script or Python builder file using `PyInstaller`:
   - Must bundle required static assets (folders like `assets/`).
   - Must successfully wrap third-party DLLs (Psycopg2 drivers, Qt graphical wrappers).
   - Configures application manifest metadata (App Version, Developer Name, Custom Application Icon).
Explain how to structure imports to avoid circular reference bugs and solve typical asset path resolution issues using `sys._MEIPASS` when running in a compiled environment.
```

## 📦 Production Compiling Workflow (Generating .exe)
When development phases are finalized and the system is ready for client deployment, follow this specific process to pack the files down using PyInstaller[cite: 13].

1. Preparation Checks
Ensure all third-party modules are added inside the internal package environment (pip install pyinstaller).

Verify that your asset references are pointing to the runtime context configuration utility function (get_asset_path()).

Place a valid .ico asset file inside your folder architecture (e.g., assets/app_icon.ico) to act as the program icon image.

2. Execution Build Command
Run the following build string in your command terminal from your root repository location:

Bash
```text
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="VermiCompostSuite" main.py
```
### Key Parameter Definitions:
1. --noconfirm: Automatically overwrite the previous build export directory if it already exists without stopping execution.

2. --onedir: Packs compilation components inside a singular, high-performance distributed directory containing the main binary. (Recommended over --onefile for apps depending on large dynamic GUI extensions like PyQt6 to prevent structural load delays during application startup).

3. --windowed: Suppresses the opening of an unstyled background Windows console terminal window while running the user layout.

4. --add-data "assets;assets": Collects resources from the local development system folder and copies them explicitly into the final executable package framework.

---

## How to Create the .ico from a logo

### Steps:

1. Make sure your real logo file is already placed at assets/logo.png (replacing the empty placeholder).
2. Open a terminal/command prompt in your project root (vermi_sales_app/ — same level as main.py).
3. Run:
```bash
pip install pillow

python -c "from PIL import Image; Image.open('assets/logo.png').save('assets/app_icon.ico', sizes=[(16,16),(32,32),(48,48),(256,256)])"
```
This runs the two lines directly without needing to save a .py file. If it works silently (no output), it succeeded.

### Alternative — save it as a small script instead:

1. Create a new file make_icon.py in your project root with:
```bash
from PIL import Image
Image.open("assets/logo.png").save("assets/app_icon.ico", sizes=[(16,16),(32,32),(48,48),(256,256)])
print("app_icon.ico created successfully.")
```
2. Run it: python make_icon.py
3. You can delete make_icon.py afterward — it's a one-time tool, not part of the app.

Check it worked:
```bash
dir assets
```
You should now see both logo.png and app_icon.ico listed, with app_icon.ico having a non-zero size.

### Common issues:

1. FileNotFoundError: assets/logo.png → you're not running the command from the project root, or the logo file isn't there yet/has a different name.
2. If your logo.png isn't square, the .ico may look stretched — crop it to a square first for best results.

Once app_icon.ico exists, the APP_ICON_PATH logic in company_config.py will pick it up automatically — no further code changes needed.


