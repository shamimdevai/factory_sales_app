from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFileDialog, QFormLayout, QMessageBox,
    QDialog, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QBuffer, QIODevice, QByteArray
from PyQt6.QtGui import QPixmap, QFont, QImage, QPainter
from src.config import theme


class SignatureEditorDialog(QDialog):
    """Lets the operator scale a signature image before it's saved. Pure GUI --
    composites the final PNG bytes itself but never touches the DB; the
    controller just persists whatever get_signature_bytes() returns.

    The output is always composited onto a fixed theme.SIGNATURE_MAX_WIDTH x
    theme.SIGNATURE_MAX_HEIGHT transparent canvas (Global Rule #4's storage
    ceiling). The scale slider controls how much of that canvas the image
    fills: below 100% it's centered with transparent padding (fixes a
    signature that looked too large/edge-to-edge before); above 100% it's
    zoomed in and overflow is clipped at the canvas edge (fixes a signature
    that looked too small because of blank margins around it in the source
    photo)."""

    _PREVIEW_MAGNIFICATION = 3  # on-screen preview is shown 3x actual size for visibility

    def __init__(self, parent, source_image: QImage):
        super().__init__(parent)
        self.setWindowTitle("Adjust Signature Size")
        self._source_image = source_image
        self._scale_percent = 100

        canvas_w = theme.SIGNATURE_MAX_WIDTH * self._PREVIEW_MAGNIFICATION
        canvas_h = theme.SIGNATURE_MAX_HEIGHT * self._PREVIEW_MAGNIFICATION

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        hint = QLabel(
            "Drag the slider until the signature looks right. It will be saved at "
            f"{theme.SIGNATURE_MAX_WIDTH}×{theme.SIGNATURE_MAX_HEIGHT}px."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"border: none; color: {theme.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(hint)

        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(canvas_w, canvas_h)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet(
            f"QLabel {{ background-color: #ffffff; border: 2px dashed {theme.BORDER_COLOR}; border-radius: 4px; }}"
        )
        layout.addWidget(self.lbl_preview, alignment=Qt.AlignmentFlag.AlignHCenter)

        slider_row = QHBoxLayout()
        lbl_small = QLabel("Smaller")
        lbl_small.setStyleSheet("border: none;")
        slider_row.addWidget(lbl_small)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(20, 200)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_row.addWidget(self.slider)
        lbl_large = QLabel("Larger")
        lbl_large.setStyleSheet("border: none;")
        slider_row.addWidget(lbl_large)
        layout.addLayout(slider_row)

        self.lbl_percent = QLabel("100%")
        self.lbl_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_percent.setStyleSheet("border: none; font-weight: bold;")
        layout.addWidget(self.lbl_percent)

        btn_reset = QPushButton("Reset to Best Fit (100%)")
        btn_reset.clicked.connect(lambda: self.slider.setValue(100))
        layout.addWidget(btn_reset)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save Signature")
        btn_save.setStyleSheet(
            "QPushButton { background-color: #1abc9c; color: white; padding: 8px 16px; "
            "font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #16a085; }"
        )
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self._on_slider_changed(100)

    def _composite(self) -> QImage:
        """Renders the source image, scaled by the current slider %, centered on a
        transparent theme.SIGNATURE_MAX_WIDTH x theme.SIGNATURE_MAX_HEIGHT canvas."""
        max_w, max_h = theme.SIGNATURE_MAX_WIDTH, theme.SIGNATURE_MAX_HEIGHT
        src = self._source_image
        fit_scale = min(max_w / src.width(), max_h / src.height())
        final_scale = fit_scale * (self._scale_percent / 100.0)

        scaled = src.scaled(
            max(1, round(src.width() * final_scale)),
            max(1, round(src.height() * final_scale)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        canvas = QImage(max_w, max_h, QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        x = (max_w - scaled.width()) // 2
        y = (max_h - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()
        return canvas

    def _on_slider_changed(self, value: int):
        self._scale_percent = value
        self.lbl_percent.setText(f"{value}%")
        composited = self._composite()
        preview_pixmap = QPixmap.fromImage(composited).scaled(
            self.lbl_preview.width(), self.lbl_preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )
        self.lbl_preview.setPixmap(preview_pixmap)

    def get_signature_bytes(self) -> bytes:
        """Call only after exec() returns Accepted. Returns final PNG bytes at
        theme.SIGNATURE_MAX_WIDTH x theme.SIGNATURE_MAX_HEIGHT."""
        canvas = self._composite()
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        canvas.save(buffer, "PNG")
        return byte_array.data()


class ProfileView(QWidget):
    save_profile_requested = pyqtSignal(str, str, str, str)  # Name, Username, Email, Password
    signature_saved = pyqtSignal(bytes)      # Final composited PNG bytes, ready to persist as-is
    signature_delete_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current_signature_bytes = None

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
        form_frame.setStyleSheet(theme.card_frame_style())
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
        input_style = theme.input_style("QLineEdit")
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
        sig_frame.setStyleSheet(theme.card_frame_style())
        sig_layout = QVBoxLayout(sig_frame)
        sig_layout.setContentsMargins(20, 20, 20, 20)

        lbl_sig = QLabel("Digital Signature")
        lbl_sig.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_sig.setStyleSheet("border: none; color: #2c3e50;")
        sig_layout.addWidget(lbl_sig)

        self.lbl_sig_preview = QLabel("No Signature Loaded")
        self.lbl_sig_preview.setStyleSheet(f"QLabel {{ background-color: #f8f9fa; border: 2px dashed {theme.BORDER_COLOR}; border-radius: 4px; color: {theme.TEXT_MUTED}; }}")
        self.lbl_sig_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sig_preview.setFixedSize(260, 100)
        sig_layout.addWidget(self.lbl_sig_preview)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_upload = QPushButton("📁 Upload")
        self.btn_upload.setStyleSheet("QPushButton { background-color: #34495e; color: white; padding: 8px; font-weight: bold; border-radius: 4px; } QPushButton:hover { background-color: #2c3e50; }")
        self.btn_upload.clicked.connect(self._on_upload_clicked)
        btn_row.addWidget(self.btn_upload)

        self.btn_edit_sig = QPushButton("✏️ Resize")
        self.btn_edit_sig.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; padding: 8px; font-weight: bold; border-radius: 4px; } "
            "QPushButton:hover { background-color: #d68910; } QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.btn_edit_sig.clicked.connect(self._on_edit_clicked)
        self.btn_edit_sig.setEnabled(False)
        btn_row.addWidget(self.btn_edit_sig)

        self.btn_delete_sig = QPushButton("🗑️ Delete")
        self.btn_delete_sig.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; padding: 8px; font-weight: bold; border-radius: 4px; } "
            "QPushButton:hover { background-color: #c0392b; } QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.btn_delete_sig.clicked.connect(self._on_delete_clicked)
        self.btn_delete_sig.setEnabled(False)
        btn_row.addWidget(self.btn_delete_sig)

        sig_layout.addLayout(btn_row)

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
        if not filepath:
            return
        image = QImage(filepath)
        if image.isNull():
            QMessageBox.warning(self, "Invalid Image", "Could not read the chosen image file.")
            return
        self._open_editor(image)

    def _on_edit_clicked(self):
        """Re-opens the resize editor on the CURRENTLY SAVED signature -- no
        need to re-pick a file just to change the scale."""
        if not self._current_signature_bytes:
            return
        image = QImage()
        image.loadFromData(self._current_signature_bytes)
        if image.isNull():
            QMessageBox.warning(self, "Error", "Could not load the current signature for editing.")
            return
        self._open_editor(image)

    def _open_editor(self, image: QImage):
        dialog = SignatureEditorDialog(self, image)
        if dialog.exec():
            self.signature_saved.emit(dialog.get_signature_bytes())

    def _on_delete_clicked(self):
        confirm = QMessageBox.question(
            self, "Delete Signature",
            "Remove the saved digital signature? PDFs issued after this will show no signature "
            "until a new one is uploaded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.signature_delete_requested.emit()

    def load_user_profile(self, name, username, email):
        self.txt_name.setText(name)
        self.txt_username.setText(username)
        self.txt_email.setText(email)

    def set_signature_data(self, png_bytes):
        """Single entry point for reflecting the saved signature on screen --
        called on page load and after every save/delete. Also gates the
        Edit/Delete buttons, since both need an existing signature to act on.
        png_bytes: bytes | None"""
        self._current_signature_bytes = png_bytes
        has_signature = bool(png_bytes)
        self.btn_edit_sig.setEnabled(has_signature)
        self.btn_delete_sig.setEnabled(has_signature)

        if has_signature:
            pixmap = QPixmap()
            pixmap.loadFromData(png_bytes)
            self.lbl_sig_preview.setPixmap(pixmap.scaled(
                self.lbl_sig_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.lbl_sig_preview.setPixmap(QPixmap())
            self.lbl_sig_preview.setText("No Signature Loaded")