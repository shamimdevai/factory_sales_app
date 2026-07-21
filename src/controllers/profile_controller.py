from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, QBuffer, QIODevice, QByteArray
from src.database.connection import get_db_session
from src.database.models import User
from src.views.profile_view import ProfileView
from PyQt6.QtWidgets import QMessageBox


class ProfileController:
    def __init__(self, view: ProfileView):
        self.view = view
        self.view.save_profile_requested.connect(self.update_user_profile)
        self.view.signature_uploaded.connect(self.process_and_save_signature)
        self.load_operator_profile()

    def load_operator_profile(self):
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                if user:
                    self.view.load_user_profile(user.name, user.username, user.email)
                    if user.digital_signature:
                        # Convert binary BYTEA stream back into a Qt QPixmap
                        pixmap = QPixmap()
                        pixmap.loadFromData(user.digital_signature)
                        self.view.set_signature_preview(pixmap)
        except Exception as e:
            print(f"[Profile Query Failure]: {e}")

    def update_user_profile(self, name, username, email, password):
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                if not user:
                    user = User(name=name, username=username, email=email, password_hash="default_hash")
                    session.add(user)
                else:
                    user.name = name
                    user.username = username
                    user.email = email
                    if password:
                        user.password_hash = password  # Stored simply for project scope (use hashed values in prod)

                session.commit()
                QMessageBox.information(self.view, "Profile Updated",
                                        "Operator personal information saved successfully!")
        except Exception as e:
            QMessageBox.critical(self.view, "Save Failed", str(e))

    def process_and_save_signature(self, filepath: str):
        try:
            # 1. Load and scale image to normalize resolutions (Max 200x80px)
            image = QImage(filepath)
            if image.isNull():
                raise ValueError("Could not read or parse chosen signature image file.")

            scaled_image = image.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)

            # 2. Serialize image object into a raw byte stream
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            scaled_image.save(buffer, "PNG")  # Keep formatting uniform as transparent/lossless PNG
            binary_signature_data = byte_array.data()

            # 3. Commit bytes directly to PostgreSQL
            with get_db_session() as session:
                user = session.query(User).first()
                if user:
                    user.digital_signature = binary_signature_data
                    session.commit()

                    # Update screen preview
                    pixmap = QPixmap.fromImage(scaled_image)
                    self.view.set_signature_preview(pixmap)
                    QMessageBox.information(self.view, "Success",
                                            "Digital signature updated and saved inside database successfully!")
                else:
                    QMessageBox.warning(self.view, "Missing Profile",
                                        "Please save your operator personal data first before uploading a signature.")

        except Exception as e:
            QMessageBox.critical(self.view, "Signature Processing Error", str(e))