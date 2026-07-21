import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QIcon
from src.database.connection import init_db
from src.views.main_window import MainWindow
from src.config import company_config as cfg
from src.config import theme


def apply_light_theme(app: QApplication):
    """Forces a consistent light palette regardless of OS dark mode, so
    default-styled QLabels (e.g. QFormLayout row labels) stay visible.
    Colors pulled from src/config/theme.py — edit that file to re-theme the app."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(theme.PAGE_BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme.CARD_BACKGROUND))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f8f9fa"))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme.CARD_BACKGROUND))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme.CARD_BACKGROUND))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme.CARD_BACKGROUND))
    app.setPalette(palette)
    # safety net
    app.setStyleSheet(f"""
        QLabel {{ color: {theme.TEXT_PRIMARY}; }}
        {theme.combobox_dropdown_style()}
    """)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    print("[System]: Initializing database schema and validation models...")
    init_db()

    print("[System]: Launching Qt Graphics Pipeline...")
    app = QApplication(sys.argv)
    if cfg.APP_ICON_PATH:
        app.setWindowIcon(QIcon(cfg.APP_ICON_PATH))
    app.setStyle('Fusion')
    apply_light_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()