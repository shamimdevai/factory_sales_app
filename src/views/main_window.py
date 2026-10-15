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
from src.views.customer_view import CustomerView
from src.views.settings_view import SettingsView

# Controllers
from src.controllers.dashboard_controller import DashboardController
from src.controllers.invoice_controller import InvoiceController
from src.controllers.history_controller import HistoryController
from src.controllers.profile_controller import ProfileController
from src.controllers.customer_controller import CustomerController
from src.controllers.settings_controller import SettingsController

#Config
from src.config import company_config as cfg
from src.config import theme

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sales Invoice Generator")
        self._apply_dynamic_minimum_size()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sidebar Panel
        # NOTE: no setFixedWidth here anymore -- the wrapping QScrollArea below
        # owns the fixed width (theme.SIDEBAR_WIDTH), and widgetResizable(True)
        # makes this frame match it. This frame's height is now allowed to
        # exceed the window's visible height without ever overlapping -- it
        # just scrolls, exactly like every page's content already does via
        # _wrap_scrollable().
        sidebar = QFrame()
        sidebar.setStyleSheet(f"QFrame {{ background-color: {theme.SIDEBAR_BACKGROUND}; border: none; }}")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 30)
        sidebar_layout.setSpacing(10)

        # Logo + brand stay at a fixed, always-legible size. The sidebar's own
        # QScrollArea (below) is what handles a too-small window -- it just
        # scrolls -- so there's no need to also shrink the logo/text dynamically;
        # that was actually making the logo look small even on normal-sized
        # windows whenever height dropped under the old 650px breakpoint.
        if cfg.COMPANY_LOGO_PATH:
            logo_size = theme.sidebar_logo_size()
            logo_lbl = QLabel()
            pix = QPixmap(cfg.COMPANY_LOGO_PATH).scaled(
                logo_size, logo_size,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Wrapped in its own stretch-padded row so it's GUARANTEED centered
            # horizontally, regardless of the label's own sizeHint width or any
            # scrollbar-driven width quirks from the sidebar's QScrollArea --
            # more reliable than relying on setAlignment() alone.
            logo_row = QHBoxLayout()
            logo_row.addStretch()
            logo_row.addWidget(logo_lbl)
            logo_row.addStretch()
            sidebar_layout.addLayout(logo_row)

        brand_label = QLabel("Chashi-Bondhu\nSales Management")
        brand_label.setFont(QFont("Segoe UI", theme.SIDEBAR_BRAND_FONT_SIZE, QFont.Weight.Bold))
        brand_label.setStyleSheet("color: #ecf0f1; margin-bottom: 25px;")
        brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_row = QHBoxLayout()
        brand_row.addStretch()
        brand_row.addWidget(brand_label)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

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
        self.btn_customers = QPushButton("👥 Customers")
        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_profile = QPushButton("👤 Operator Profile")

        self._nav_buttons = [
            self.btn_dashboard, self.btn_invoice, self.btn_history,
            self.btn_customers, self.btn_settings, self.btn_profile
        ]
        for btn in self._nav_buttons:
            btn.setStyleSheet(btn_style)
            btn.setCheckable(True)
            sidebar_layout.addWidget(btn)

        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.clicked.connect(lambda: self._switch_view(0, self.btn_dashboard))
        self.btn_invoice.clicked.connect(lambda: self._switch_view(1, self.btn_invoice))
        self.btn_history.clicked.connect(lambda: self._switch_view(2, self.btn_history))
        self.btn_customers.clicked.connect(lambda: self._switch_view(3, self.btn_customers))
        self.btn_settings.clicked.connect(lambda: self._switch_view(4, self.btn_settings))
        self.btn_profile.clicked.connect(lambda: self._switch_view(5, self.btn_profile))

        sidebar_layout.addStretch()

        footer = QLabel("v1.1.0 Production\nDeveloped By Shamimdevai")
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
        self.customer_view = CustomerView()
        self.settings_view = SettingsView()
        self.profile_view = ProfileView()

        self.dashboard_controller = DashboardController(self.dashboard_view)
        self.invoice_controller = InvoiceController(self.invoice_view)
        self.history_controller = HistoryController(self.history_view)
        self.customer_controller = CustomerController(self.customer_view)
        self.settings_controller = SettingsController(self.settings_view)
        self.profile_controller = ProfileController(self.profile_view)

        # Cross-page navigation: Customers page's "View Ledger" action jumps to
        # History Ledger pre-filtered to that customer. This lives here (not in
        # either controller) so CustomerController/HistoryController stay decoupled.
        self.customer_view.view_ledger_requested.connect(self._go_to_customer_ledger)

        # Wrap each screen in a QScrollArea so content scrolls instead of
        # clipping on smaller screens/resolutions
        self.stacked_widget.addWidget(self._wrap_scrollable(self.dashboard_view))  # Index 0
        self.stacked_widget.addWidget(self._wrap_scrollable(self.invoice_view))    # Index 1
        self.stacked_widget.addWidget(self._wrap_scrollable(self.history_view))    # Index 2
        self.stacked_widget.addWidget(self._wrap_scrollable(self.customer_view))   # Index 3
        self.stacked_widget.addWidget(self._wrap_scrollable(self.settings_view))   # Index 4
        self.stacked_widget.addWidget(self._wrap_scrollable(self.profile_view))    # Index 5

        # Wrapping the sidebar itself in a scroll area is what actually fixes
        # small-window overlap: if the sidebar's real content (logo + brand +
        # nav buttons + footer) needs more height than the window currently
        # has, it now scrolls internally instead of Qt drawing everything
        # overlapping on top of each other (which is what a fixed-height
        # QFrame with no scroll area does when it's squeezed below its
        # natural minimum size).
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidget(sidebar)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(theme.SIDEBAR_WIDTH)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setStyleSheet(f"QScrollArea {{ background-color: {theme.SIDEBAR_BACKGROUND}; border: none; }}")

        layout.addWidget(sidebar_scroll)
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
        for btn in self._nav_buttons:
            btn.setChecked(False)

        active_button.setChecked(True)
        self.stacked_widget.setCurrentIndex(index)

        if index == 0:
            self.dashboard_controller.refresh_dashboard_data(self.dashboard_view.get_current_period())
        elif index == 1:
            # Keeps the customer picker and product dropdown in sync with
            # anything added/edited on the Customers or Settings pages since
            # this page was last shown.
            self.invoice_controller.refresh_customer_list()
            self.invoice_controller.refresh_product_list()
        elif index == 2:
            self.history_controller.load_records(self.history_view.get_current_filter())
        elif index == 3:
            self.customer_controller.refresh_all()
        elif index == 4:
            self.settings_controller.refresh_all()

    def _go_to_customer_ledger(self, customer_id: int, customer_name: str):
        """Customers page 'View Ledger' -> History Ledger, pre-filtered.
        Order matters: apply the filter first so that when _switch_view's own
        index==2 branch calls load_records(get_current_filter()), it picks up
        the same customer_id override rather than the default date-range."""
        self.history_controller.show_customer_ledger(customer_id, customer_name)
        self._switch_view(2, self.btn_history)
