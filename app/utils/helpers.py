from flask import session, request
from flask_login import current_user
from app.models.user import Role

# NOTE: file-upload handling (save_upload, allowed_file) moved to
# app.services.storage_service - use save_image()/save_document() there
# instead. Kept out of this module so there's exactly one place uploads are
# validated, error-handled, and (eventually) backed by object storage.


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
