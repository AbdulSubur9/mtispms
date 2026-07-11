from functools import wraps
from flask import abort
from flask_login import current_user


def roles_required(*roles):
    """Restrict a view to users whose role is in `roles`."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def school_scoped(view_func):
    """Ensures non-super-admin users only ever operate within their own school.
    Injects nothing; relies on views to filter querysets by current_user.school_id.
    This decorator simply blocks users with no school assigned (other than super admin).
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        from app.models.user import Role
        if current_user.role != Role.SUPER_ADMIN and current_user.school_id is None:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped


def write_access_required(view_func):
    """Blocks read-only roles (Teacher) from create/edit/delete views."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        from app.models.user import Role
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role == Role.TEACHER:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapped
