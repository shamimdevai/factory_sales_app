from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFileDialog, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

class ProfileView(QWidget):
    save_profile_requested = pyqtSignal(str, str, str, str) # Name, Username, Email, Password
    signature_uploaded = pyqtSignal(str) # Path to signature image

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        title = QLabel("Operator User Profile Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        self.main_layout.addWidget(title)

        self._init_profile_form()

    def _init_profile_form(self):
        container = QHBoxLayout()
        container.setSpacing(30)

        # 1. Left side: Form Inputs
        form_frame = QFrame()
        form_frame.setStyleSheet("QFrame { background-color: white; border-radius: 6px; border: 1px solid #cbd5e1; }")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("Personal Data")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("border: none; color: #2c3e50;")
        form_layout.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_name = QLineEdit()
        self.txt_username = QLineEdit()
        self.txt_email = QLineEdit()
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Leave blank to keep current password")

        # Basic input Styling
        input_style = "QLineEdit { padding: 6px; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; color: #2c3e50; }"
        for f in [self.txt_name, self.txt_username, self.txt_email, self.txt_password]:
            f.setStyleSheet(input_style)

        form.addRow("Display Name *:", self.txt_name)
        form.addRow("Username *:", self.txt_username)
        form.addRow("Email Address *:", self.txt_email)
        form.addRow("Reset Password:", self.txt_password)

        form_layout.addLayout(form)
        form_layout.addSpacing(15)

        btn_save = QPushButton("💾 Update Profile Info")
        btn_save.setStyleSheet("QPushButton { background-color: #1abc9c; color: white; padding: 10px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #16a085; }")
        btn_save.clicked.connect(self._on_save_clicked)
        form_layout.addWidget(btn_save)

        # 2. Right side: Signature Upload Widget
        sig_frame = QFrame()
        sig_frame.setFixedWidth(300)
        sig_frame.setStyleSheet("QFrame { background-color: white; border-radius: 6px; border: 1px solid #cbd5e1; }")
        sig_layout = QVBoxLayout(sig_frame)
        sig_layout.setContentsMargins(20, 20, 20, 20)

        lbl_sig = QLabel("Digital Signature")
        lbl_sig.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_sig.setStyleSheet("border: none; color: #2c3e50;")
        sig_layout.addWidget(lbl_sig)

        self.lbl_sig_preview = QLabel("No Signature Loaded")
        self.lbl_sig_preview.setStyleSheet("QLabel { background-color: #f8f9fa; border: 2px dashed #cbd5e1; border-radius: 4px; color: #7f8c8d; }")
        self.lbl_sig_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sig_preview.setFixedSize(260, 100)
        sig_layout.addWidget(self.lbl_sig_preview)

        btn_upload = QPushButton("📁 Upload Signature Image")
        btn_upload.setStyleSheet("QPushButton { background-color: #34495e; color: white; padding: 8px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2c3e50; }")
        btn_upload.clicked.connect(self._on_upload_clicked)
        sig_layout.addWidget(btn_upload)

        container.addWidget(form_frame, 3)
        container.addWidget(sig_frame, 2)

        self.main_layout.addLayout(container)
        self.main_layout.addStretch()

    def _on_save_clicked(self):
        if not self.txt_name.text().strip() or not self.txt_username.text().strip() or not self.txt_email.text().strip():
            QMessageBox.warning(self, "Invalid Fields", "Name, Username, and Email are required.")
            return
        self.save_profile_requested.emit(
            self.txt_name.text().strip(),
            self.txt_username.text().strip(),
            self.txt_email.text().strip(),
            self.txt_password.text().strip()
        )

    def _on_upload_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Signature Image", "", "Images (*.png *.jpg *.jpeg)")
        if filepath:
            self.signature_uploaded.emit(filepath)

    def load_user_profile(self, name, username, email):
        self.txt_name.setText(name)
        self.txt_username.setText(username)
        self.txt_email.setText(email)

    def set_signature_preview(self, pixmap: QPixmap):
        """Displays a scaled rendering of the user's active signature on screen."""
        if not pixmap.isNull():
            self.lbl_sig_preview.setPixmap(pixmap.scaled(
                self.lbl_sig_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.lbl_sig_preview.setText("No Signature Loaded")