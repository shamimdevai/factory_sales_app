# Vermi-Compost Factory Management Suite

A professional Windows desktop application tailored for the automated tracking, operations management, and invoice provisioning of a Vermi-composting factory. Built specifically to handle primary product lines (**Vermi-compost** and **Earthworms**), this application transitions legacy spreadsheet-based operations into a modern, highly secure database-driven transactional engine.

---

## 🚀 Key Features

*   **Interactive Invoice Terminal (Decoupled MVC Layout):** 
    *   Dual-panel transaction designer separating client details from transactional workflows.
    *   Live reactive cart management supporting dynamic item entry, volume/pricing multipliers, and row deletions.
    *   Inline metadata captures payment states (`Paid`, `Unpaid`, `Partial`).
    *   Real-time processing for Subtotals, 5% standard system tax, and grand transactional balances.
*   **Operational Dashboard Analytics:** High-impact metric panels compiling monthly revenues, compound volumes sold (kg), live earthworm sales metrics, and real-time ledger updates reflecting the 5 most recent activities.
*   **Sales History Ledger:** Multi-tiered data grid housing long-term historical records. Equips operators with robust query tools to narrow scopes via specific start/end date ranges.
*   **Automated Document Exports:**
    *   **PDF Invoice Generation:** Emits pixel-perfect, single-page, print-ready records utilizing `ReportLab` including alternate row striping, client records, and secure signature integration.
    *   **Excel Ledger Utilities:** Generates clean analytical worksheets utilizing native `openpyxl` frameworks, formatting cells correctly by data type and inserting dynamic `=SUM(...)` tracking cells.
*   **Operator Profiles & Secure Signatures:** System adjustments interface including custom binary signature inputs. Image uploads are automatically processed, resized to a 200x80px bounding box, and written into PostgreSQL database targets as isolated byte-streams (`BYTEA`).

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
│   ├── database/             # Relational data wrappers
│   │   ├── connection.py     # Engine lifecycles & session context managers
│   │   └── models.py         # Declarative models (User, Customer, Invoice, InvoiceItem)
│   │
│   ├── views/                # Decoupled GUI display layers (PyQt6 Layouts)
│   │   ├── main_window.py    # Main Navigation interface
│   │   ├── dashboard_view.py # Metric tiles & top summaries
│   │   ├── invoice_view.py   # Split-pane interactive POS screen
│   │   ├── history_view.py   # Historical transactions ledger
│   │   └── profile_view.py   # Signature management & identity configs
│   │
│   ├── controllers/          # Business logic intermediaries
│   │   ├── invoice_controller.py   # Live cart calculation & atomic sales handlers
│   │   ├── dashboard_controller.py  # KPI aggregation data queries
│   │   ├── history_controller.py    # Search query parameter engines
│   │   └── profile_controller.py    # Binary image transformations
│   │
│   └── utils/                # Utility modules
│       ├── pdf_generator.py  # Structural PDF compilation scripts
│       └── excel_exporter.py # Financial spreadsheet generation tools
│
├── .env                      # Application environment variables (Git Ignored)
├── alembic.ini               # Relational target configurations
├── requirements.txt          # Python ecosystem manifest
└── main.py                   # Central execution hook
```

💻 Environment Setup & Local Installation
1. System Requirements & Prerequisites
Ensure you have Python 3.11 and a live PostgreSQL instance up and running on your local machine.

2. Clone the Repository & Configure Python Space

# Move into target file directory
cd vermi_sales_app

# Create a clean isolated virtual environment
python -m venv venv

# Activate local environment configurations
# For Windows PowerShell:
.\venv\Scripts\Activate.ps1
# For standard Command Prompt:
.\venv\Scripts\activate.bat

3. Install Environment Requirements
Bash
pip install -r requirements.txt
4. Setup Local Environment Variables
Create a file named .env in the root repository directory and paste the following, adjusting credentials to match your PostgreSQL setup:

Code snippet
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/vermi_factory_db
5. Execute Relational Migrations
Bash
# Initialize target data matrices
alembic upgrade head
6. Boot the Application
Bash
python main.py
📦 Production Compiling Workflow (Generating .exe)
When you are ready to package the system for standalone client deployment, follow this specific process to bundle it using PyInstaller.

1. Preparation Check
Verify that your system asset paths are routing dynamically inside the execution wrapper using your asset path helper, which correctly switches lookup environments when checking for runtime folders inside sys._MEIPASS.

2. Run Compilation
Execute the following string directly from the root of your application terminal workspace:

Bash
pyinstaller --noconfirm --onedir --windowed --add-data "assets;assets" --icon="assets/app_icon.ico" --name="VermiCompostSuite" main.py

3. Output Location
Once the compiler completes its task successfully:

The raw working directories can be cleaned out from the ./build folder.

Your production distribution package will be located entirely inside ./dist/VermiCompostSuite/. You can copy or distribute this folder directly to any client workstation running Windows 10/11. The application boots cleanly via VermiCompostSuite.exe.

***

### 💡 High-DPI and Text Color Note for Developers
If elements of the GUI present invisible placeholder fonts or light input fields inside specific dark desktop visual styles, check that explicit stylesheet elements have the correct text colors applied alongside background parameters (e.g., `background-color: #ffffff; color: #2c3e50;`).