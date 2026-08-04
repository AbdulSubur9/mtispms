"""
Helpers for safely committing database changes with proper error handling.

Prevents raw IntegrityError / SQLAlchemyError tracebacks from bubbling up as
generic "Internal Server Error" pages. Every create/update view should route
its commit through `safe_commit()` so failures are logged server-side and
surfaced to the user as a friendly, actionable message.
"""
from flask import current_app, flash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.extensions import db


def safe_commit(friendly_message=None, log_context=""):
    """Attempt to commit the current session.

    Returns True on success. On failure, rolls back, logs the real exception
    server-side (never shown to the user), flashes a friendly message, and
    returns False so the calling view can re-render its form instead of
    crashing.
    """
    try:
        db.session.commit()
        return True
    except IntegrityError as exc:
        db.session.rollback()
        current_app.logger.error(
            "IntegrityError during commit%s: %s",
            f" ({log_context})" if log_context else "", exc,
            exc_info=True,
        )
        message = friendly_message or (
            "That record conflicts with an existing one (a duplicate ID, "
            "username, email, or receipt/reference number). Please check "
            "your input and try again."
        )
        flash(message, "danger")
        return False
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error(
            "Database error during commit%s: %s",
            f" ({log_context})" if log_context else "", exc,
            exc_info=True,
        )
        flash("A database error occurred while saving. Please try again.", "danger")
        return False
