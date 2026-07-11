from datetime import date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import School, Notification
from app.models.user import Role
from app.services import stats_service as stats

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


def _resolve_school_id():
    """Super admins can pick a school from a dropdown (?school_id=), others are locked to their own."""
    if current_user.role == Role.SUPER_ADMIN:
        school_id = request.args.get("school_id", type=int)
        return school_id  # None = all schools
    return current_user.school_id


@dashboard_bp.route("/")
@login_required
def index():
    school_id = _resolve_school_id()
    today = date.today()
    month_start = today.replace(day=1)

    schools = School.query.order_by(School.name).all() if current_user.role == Role.SUPER_ADMIN else []

    kpis = {
        "total_students": stats.total_students(school_id),
        "today_collections": stats.collections_between(school_id, today, today),
        "monthly_collections": stats.collections_between(school_id, month_start, today),
        "total_expenses": stats.total_expenses(school_id),
        "current_balance": stats.current_balance(school_id),
    }
    paid, owing = stats.students_paid_vs_owing(school_id)
    kpis["students_paid"] = paid
    kpis["students_owing"] = owing
    kpis["outstanding_fees"] = owing

    payment_trend = stats.payment_trend(school_id, days=14)
    expense_trend = stats.expense_trend(school_id, days=14)
    category_breakdown = stats.expense_category_breakdown(school_id)

    notifications = (
        Notification.query.filter(
            (Notification.user_id == current_user.id)
            | ((Notification.user_id.is_(None)) & (Notification.school_id == current_user.school_id))
        )
        .order_by(Notification.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        schools=schools,
        selected_school_id=school_id,
        payment_trend=payment_trend,
        expense_trend=expense_trend,
        category_breakdown=category_breakdown,
        notifications=notifications,
    )
