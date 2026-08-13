from src.database.connection import get_db_session
from src.database.models import User
from src.views.profile_view import ProfileView
from PyQt6.QtWidgets import QMessageBox


class ProfileController:
    def __init__(self, view: ProfileView):
        self.view = view
        self.view.save_profile_requested.connect(self.update_user_profile)
        self.view.signature_saved.connect(self.save_signature)
        self.view.signature_delete_requested.connect(self.delete_signature)
        self.load_operator_profile()

    def load_operator_profile(self):
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                if user:
                    name, username, email = user.name, user.username, user.email
                    signature_bytes = user.digital_signature
                else:
                    name = None

            if name is not None:
                self.view.load_user_profile(name, username, email)
                self.view.set_signature_data(signature_bytes)
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
                # No manual session.commit() needed -- get_db_session() commits
                # automatically when this `with` block exits normally.

            QMessageBox.information(self.view, "Profile Updated",
                                    "Operator personal information saved successfully!")
        except Exception as e:
            QMessageBox.critical(self.view, "Save Failed", str(e))

    def save_signature(self, png_bytes: bytes):
        """png_bytes arrives already composited to theme.SIGNATURE_MAX_WIDTH x
        SIGNATURE_MAX_HEIGHT by ProfileView's SignatureEditorDialog -- this
        method's only job is persisting it."""
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                user_found = user is not None
                if user_found:
                    user.digital_signature = png_bytes

            if user_found:
                self.view.set_signature_data(png_bytes)
                QMessageBox.information(self.view, "Success", "Digital signature saved successfully!")
            else:
                QMessageBox.warning(self.view, "Missing Profile",
                                    "Please save your operator personal data first before uploading a signature.")
        except Exception as e:
            QMessageBox.critical(self.view, "Signature Save Error", str(e))

    def delete_signature(self):
        try:
            with get_db_session() as session:
                user = session.query(User).first()
                user_found = user is not None
                if user_found:
                    user.digital_signature = None

            if user_found:
                self.view.set_signature_data(None)
                QMessageBox.information(self.view, "Deleted", "Digital signature removed.")
            else:
                QMessageBox.warning(self.view, "Missing Profile", "No operator profile found.")
        except Exception as e:
            QMessageBox.critical(self.view, "Delete Failed", str(e))