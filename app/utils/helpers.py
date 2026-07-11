import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from flask_login import current_user
from app.models.user import Role


def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def save_upload(file_storage, subfolder="misc"):
    """Save an uploaded file securely, return the relative path (or None)."""
    if not file_storage or file_storage.filename == "":
        return None
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, unique_name)
    file_storage.save(path)
    return f"uploads/{subfolder}/{unique_name}"


def current_school_id():
    """Return the school id the current user should be scoped to.
    Super admins operating without an explicit school context return None (all schools)."""
    if current_user.is_authenticated:
        return current_user.school_id
    return None


def is_super_admin():
    return current_user.is_authenticated and current_user.role == Role.SUPER_ADMIN


def scope_query_to_school(query, model, school_id_override=None):
    """Apply school scoping to a SQLAlchemy query unless the user is a super admin
    viewing all schools."""
    school_id = school_id_override if school_id_override is not None else current_school_id()
    if is_super_admin() and school_id_override is None:
        return query
    return query.filter(model.school_id == school_id)
