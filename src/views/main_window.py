from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QGuiApplication

# Views
from src.views.dashboard_view import DashboardView
from src.views.invoice_view import InvoiceView
from src.views.history_view import HistoryView
from src.views.profile_view import ProfileView

# Controllers
from src.controllers.dashboard_controller import DashboardController
from src.controllers.invoice_controller import InvoiceController
from src.controllers.history_controller import HistoryController
from src.controllers.profile_controller import ProfileController

#Config
from src.config import company_config as cfg
from src.config import theme

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chashi-Bondhu Sales Management Suite")
        self._apply_dynamic_minimum_size()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sidebar Panel
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"QFrame {{ background-color: {theme.SIDEBAR_BACKGROUND}; border: none; }}")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 30)
        sidebar_layout.setSpacing(10)
        # Change LOGO size here (130, 130 to whatever you want)
        if cfg.COMPANY_LOGO_PATH:
            logo_lbl = QLabel()
            pix = QPixmap(cfg.COMPANY_LOGO_PATH).scaled(
                130, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sidebar_layout.addWidget(logo_lbl)

        brand_label = QLabel("Chashi-Bondhu\nSales Management")
        brand_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #ecf0f1; margin-bottom: 25px;")
        brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(brand_label)

        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: #bdc3c7;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme.SIDEBAR_HOVER};
                color: #ecf0f1;
            }}
            QPushButton:checked {{
                background-color: {theme.ACCENT};
                color: white;
            }}
        """

        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_invoice = QPushButton("📄 Invoice Terminal")
        self.btn_history = QPushButton("📜 Sales History Ledger")
        self.btn_profile = QPushButton("👤 Operator Profile")

        for btn in [self.btn_dashboard, self.btn_invoice, self.btn_history, self.btn_profile]:
            btn.setStyleSheet(btn_style)
            btn.setCheckable(True)
            sidebar_layout.addWidget(btn)

        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self._switch_view(0, self.btn_dashboard))
        self.btn_invoice.clicked.connect(lambda: self._switch_view(1, self.btn_invoice))
        self.btn_history.clicked.connect(lambda: self._switch_view(2, self.btn_history))
        self.btn_profile.clicked.connect(lambda: self._switch_view(3, self.btn_profile))

        sidebar_layout.addStretch()

        footer = QLabel("v1.0.0 Production\nDeveloped By Shamim")
        footer.setFont(QFont("Segoe UI", 8))
        footer.setStyleSheet("color: #7f8c8d;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(footer)

        # 2. Main Work Area Switcher
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet(f"QStackedWidget {{ background-color: {theme.PAGE_BACKGROUND}; }}")

        self.dashboard_view = DashboardView()
        self.invoice_view = InvoiceView()
        self.history_view = HistoryView()
        self.profile_view = ProfileView()

        self.dashboard_controller = DashboardController(self.dashboard_view)
        self.invoice_controller = InvoiceController(self.invoice_view)
        self.history_controller = HistoryController(self.history_view)
        self.profile_controller = ProfileController(self.profile_view)

        # Wrap each screen in a QScrollArea so content scrolls instead of
        # clipping on smaller screens/resolutions
        self.stacked_widget.addWidget(self._wrap_scrollable(self.dashboard_view))  # Index 0
        self.stacked_widget.addWidget(self._wrap_scrollable(self.invoice_view))    # Index 1
        self.stacked_widget.addWidget(self._wrap_scrollable(self.history_view))    # Index 2
        self.stacked_widget.addWidget(self._wrap_scrollable(self.profile_view))    # Index 3

        layout.addWidget(sidebar)
        layout.addWidget(self.stacked_widget)

        self.dashboard_controller.refresh_dashboard_data(self.dashboard_view.get_current_period())

    def _apply_dynamic_minimum_size(self):
        """
        The window must never be shrinkable below 1/4 of the screen's available
        size, on any monitor — rather than one fixed pixel size that's too
        large on a small laptop screen or too small on a large monitor.
        """
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            min_w = max(int(available.width() * 0.25), 480)
            min_h = max(int(available.height() * 0.25), 400)
        else:
            min_w, min_h = 480, 400
        self.setMinimumSize(min_w, min_h)

    @staticmethod
    def _wrap_scrollable(view: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidget(view)
        scroll.setWidgetResizable(True)
        # Explicit "as needed" policy: a horizontal AND vertical scrollbar
        # appears automatically whenever a page's content doesn't fit the
        # window — on every page — instead of content silently clipping.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.PAGE_BACKGROUND}; border: none; }}")
        return scroll

    def _switch_view(self, index: int, active_button: QPushButton):
        for btn in [self.btn_dashboard, self.btn_invoice, self.btn_history, self.btn_profile]:
            btn.setChecked(False)

        active_button.setChecked(True)
        self.stacked_widget.setCurrentIndex(index)

        if index == 0:
            self.dashboard_controller.refresh_dashboard_data(self.dashboard_view.get_current_period())
        elif index == 2:
            self.history_controller.load_records(self.history_view.get_current_filter())