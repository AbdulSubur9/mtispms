import os
import uuid
from flask import current_app, session, request
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


def is_super_admin():
    return current_user.is_authenticated and current_user.role == Role.SUPER_ADMIN


def current_school_id():
    """Return the school id the current user should be scoped to.

    - Non-super-admin users are ALWAYS scoped to their own school - this is
      the tenant boundary and is never overridable via URL/session tampering.
    - Super Admins may switch between an explicit per-school view and a
      combined "All Schools" view. Their choice is read from ?school_id= on
      the current request (which also updates the sticky session value) and
      falls back to whatever they last selected. Until they pick a school,
      they see the combined view - this is an explicit choice they make via
      the school switcher, not an accidental cross-tenant leak.
    """
    if not current_user.is_authenticated:
        return None

    if not is_super_admin():
        return current_user.school_id

    if "school_id" in request.args:
        raw = request.args.get("school_id", type=int)
        session["active_school_id"] = raw or None
        return session["active_school_id"]

    return session.get("active_school_id")


def scope_query_to_school(query, model, school_id_override=None):
    """Apply school scoping to a SQLAlchemy query.

    Every list/detail view should route through this (or check
    `current_school_id()` directly) rather than querying a model
    unfiltered - that is precisely the class of bug that let a Super
    Admin's combined view leak into what should have been a single-school
    view, and (more seriously) would let a School Admin see another
    school's data if a view ever forgot the filter.
    """
    school_id = school_id_override if school_id_override is not None else current_school_id()
    if is_super_admin() and school_id_override is None and school_id is None:
        # Explicit combined view chosen by the Super Admin (no school selected).
        return query
    return query.filter(model.school_id == school_id)
