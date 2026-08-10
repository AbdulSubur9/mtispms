from datetime import date, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import School, Notification, Payment, ClassRoom, Attendance
from app.models.user import Role
from app.services import stats_service as stats
from app.utils.helpers import current_school_id

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")

FINANCIAL_ROLES = (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN, Role.ACCOUNTANT)


@dashboard_bp.route("/")
@login_required
def index():
    # Uses the shared current_school_id() helper so the Super Admin's school
    # selection here is the SAME sticky selection that scopes every other
    # page (students, payments, expenses, reports) - picking a school once
    # filters the whole app, not just this dashboard.
    school_id = current_school_id()

    if current_user.role == Role.COLLECTOR:
        return _collector_dashboard(school_id)
    if current_user.role == Role.TEACHER:
        return _teacher_dashboard(school_id)
    return _financial_dashboard(school_id)


def _financial_dashboard(school_id):
    """Super Admin / School Admin / Accountant view - full financial
    picture. Never rendered for Collector or Teacher roles (see the two
    functions below), and the underlying figures are never computed for
    those roles either - not just hidden in the template."""
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

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        schools=schools,
        selected_school_id=school_id,
        payment_trend=payment_trend,
        expense_trend=expense_trend,
        category_breakdown=category_breakdown,
        notifications=_notifications(),
    )


def _collector_dashboard(school_id):
    """Collector view - deliberately excludes total revenue, current
    balance, expenses, and profit/loss (sections 6 & 12). Shows only what a
    Collector needs to do their job: their OWN collection activity and a
    fast path into search/record-payment."""
    today = date.today()
    month_start = today.replace(day=1)

    my_today_query = Payment.query.filter(
        Payment.collector_id == current_user.id, Payment.is_void.is_(False), Payment.payment_date == today
    )
    my_month_query = Payment.query.filter(
        Payment.collector_id == current_user.id, Payment.is_void.is_(False),
        Payment.payment_date >= month_start, Payment.payment_date <= today,
    )
    from app.extensions import db

    my_today_total = float(
        my_today_query.with_entities(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0
    )
    my_today_count = my_today_query.count()
    my_month_total = float(
        my_month_query.with_entities(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0
    )
    my_month_count = my_month_query.count()

    recent_payments = (
        Payment.query.filter(Payment.collector_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(8)
        .all()
    )

    return render_template(
        "dashboard/collector.html",
        my_today_total=my_today_total, my_today_count=my_today_count,
        my_month_total=my_month_total, my_month_count=my_month_count,
        recent_payments=recent_payments, notifications=_notifications(),
    )


def _teacher_dashboard(school_id):
    """Teacher view - academic-focused, zero financial data (section 12).
    Shows assigned classes, attendance status for today, and recent exams."""
    from app.models import Exam

    my_classes = ClassRoom.query.filter(ClassRoom.teacher_id == current_user.id).order_by(ClassRoom.name).all()
    class_ids = [c.id for c in my_classes]

    today = date.today()
    attendance_taken_today = set()
    if class_ids:
        rows = (
            Attendance.query.filter(Attendance.class_id.in_(class_ids), Attendance.attendance_date == today)
            .with_entities(Attendance.class_id)
            .distinct()
            .all()
        )
        attendance_taken_today = {r[0] for r in rows}

    recent_exams = (
        Exam.query.filter(Exam.class_id.in_(class_ids)).order_by(Exam.created_at.desc()).limit(5).all()
        if class_ids else []
    )

    return render_template(
        "dashboard/teacher.html",
        my_classes=my_classes, attendance_taken_today=attendance_taken_today,
        recent_exams=recent_exams, notifications=_notifications(),
    )


def _notifications():
    return (
        Notification.query.filter(
            (Notification.user_id == current_user.id)
            | ((Notification.user_id.is_(None)) & (Notification.school_id == current_user.school_id))
        )
        .order_by(Notification.created_at.desc())
        .limit(8)
        .all()
    )
