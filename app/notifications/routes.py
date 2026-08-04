from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Notification
from app.utils.db_safety import safe_commit

notifications_bp = Blueprint("notifications", __name__, template_folder="../templates/notifications")


def _visible_notifications_query():
    """A notification is visible to a user if it was addressed to them
    directly, or broadcast to their whole school (user_id is NULL)."""
    return Notification.query.filter(
        (Notification.user_id == current_user.id)
        | ((Notification.user_id.is_(None)) & (Notification.school_id == current_user.school_id))
    )


@notifications_bp.route("/")
@login_required
def center():
    page = request.args.get("page", 1, type=int)
    pagination = _visible_notifications_query().order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template("notifications/center.html", notifications=pagination.items, pagination=pagination)


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    notification = _visible_notifications_query().filter(Notification.id == notification_id).first_or_404()
    notification.is_read = True
    safe_commit(log_context=f"mark_read {notification_id}")
    return redirect(request.referrer or url_for("notifications.center"))


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    _visible_notifications_query().filter_by(is_read=False).update({"is_read": True}, synchronize_session=False)
    if safe_commit(log_context="mark_all_read"):
        flash("All notifications marked as read.", "info")
    return redirect(url_for("notifications.center"))
