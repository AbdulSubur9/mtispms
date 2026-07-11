from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required, current_user
from app.models import Payment, Expense, Student, User
from app.models.user import Role
from app.services import stats_service as stats
from app.services.export_service import export_csv, export_excel, export_pdf_table
from app.utils.helpers import current_school_id, is_super_admin

reports_bp = Blueprint("reports", __name__, template_folder="../templates/reports")


def _school_id():
    if current_user.role == Role.SUPER_ADMIN:
        return request.args.get("school_id", type=int)
    return current_user.school_id


def _date_range():
    period = request.args.get("period", "monthly")
    today = date.today()
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    if period == "custom" and start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    elif period == "daily":
        start_date = end_date = today
    elif period == "weekly":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == "yearly":
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:  # monthly (default)
        start_date = today.replace(day=1)
        end_date = today
    return period, start_date, end_date


@reports_bp.route("/")
@login_required
def index():
    return render_template("reports/index.html")


@reports_bp.route("/income")
@login_required
def income_report():
    school_id = _school_id()
    period, start_date, end_date = _date_range()
    query = Payment.query.filter(Payment.is_void.is_(False), Payment.payment_date >= start_date, Payment.payment_date <= end_date)
    if school_id is not None:
        query = query.filter(Payment.school_id == school_id)
    payments = query.order_by(Payment.payment_date).all()
    total = sum(float(p.amount) for p in payments)
    return render_template(
        "reports/income.html", payments=payments, total=total, period=period, start_date=start_date, end_date=end_date
    )


@reports_bp.route("/expense")
@login_required
def expense_report():
    school_id = _school_id()
    period, start_date, end_date = _date_range()
    query = Expense.query.filter(Expense.expense_date >= start_date, Expense.expense_date <= end_date)
    if school_id is not None:
        query = query.filter(Expense.school_id == school_id)
    expenses = query.order_by(Expense.expense_date).all()
    total = sum(float(e.amount) for e in expenses)
    return render_template(
        "reports/expense.html", expenses=expenses, total=total, period=period, start_date=start_date, end_date=end_date
    )


@reports_bp.route("/profit-loss")
@login_required
def profit_loss_report():
    school_id = _school_id()
    period, start_date, end_date = _date_range()
    income = stats.collections_between(school_id, start_date, end_date)
    expense = stats.expenses_between(school_id, start_date, end_date)
    net = income - expense
    opening_balance = stats.collections_between(school_id, date(2000, 1, 1), start_date - timedelta(days=1)) - \
        stats.expenses_between(school_id, date(2000, 1, 1), start_date - timedelta(days=1))
    closing_balance = opening_balance + net
    category_breakdown = stats.expense_category_breakdown(school_id)
    return render_template(
        "reports/profit_loss.html", income=income, expense=expense, net=net,
        opening_balance=opening_balance, closing_balance=closing_balance,
        category_breakdown=category_breakdown, period=period, start_date=start_date, end_date=end_date,
    )


@reports_bp.route("/collector-performance")
@login_required
def collector_performance_report():
    school_id = _school_id()
    period, start_date, end_date = _date_range()
    rows = stats.collector_performance(school_id, start_date, end_date)
    collectors = {u.id: u for u in User.query.filter(User.id.in_([r[0] for r in rows])).all()} if rows else {}
    data = [(collectors.get(r[0]).full_name if collectors.get(r[0]) else "Unknown", r[1], float(r[2])) for r in rows]
    return render_template("reports/collector_performance.html", data=data, period=period, start_date=start_date, end_date=end_date)


@reports_bp.route("/student-history/<int:student_id>")
@login_required
def student_payment_history(student_id):
    student = Student.query.get_or_404(student_id)
    payments = student.payments.order_by(Payment.payment_date.desc()).all()
    return render_template("reports/student_history.html", student=student, payments=payments)


@reports_bp.route("/outstanding")
@login_required
def outstanding_report():
    school_id = _school_id()
    query = Student.query.filter(Student.status == "active")
    if school_id is not None:
        query = query.filter(Student.school_id == school_id)
    students = query.order_by(Student.first_name).all()

    today = date.today()
    month_start = today.replace(day=1)
    paid, owing = stats.students_paid_vs_owing(school_id, month_start, today)

    paid_ids = {
        p.student_id
        for p in Payment.query.filter(
            Payment.is_void.is_(False), Payment.payment_date >= month_start, Payment.payment_date <= today
        ).all()
        if school_id is None or p.school_id == school_id
    }
    outstanding_students = [s for s in students if s.id not in paid_ids]
    return render_template("reports/outstanding.html", students=outstanding_students, paid=paid, owing=owing)


@reports_bp.route("/export/<report_type>/<fmt>")
@login_required
def export_report(report_type, fmt):
    school_id = _school_id()
    period, start_date, end_date = _date_range()

    if report_type == "income":
        query = Payment.query.filter(Payment.is_void.is_(False), Payment.payment_date >= start_date, Payment.payment_date <= end_date)
        if school_id is not None:
            query = query.filter(Payment.school_id == school_id)
        rows_data = query.order_by(Payment.payment_date).all()
        headers = ["Receipt #", "Student", "Type", "Amount", "Date", "Collector"]
        rows = [
            [p.receipt_number, p.student.full_name, p.payment_type_label, float(p.amount),
             p.payment_date.isoformat(), p.collector.full_name]
            for p in rows_data
        ]
        title = "Income Report"
    elif report_type == "expense":
        query = Expense.query.filter(Expense.expense_date >= start_date, Expense.expense_date <= end_date)
        if school_id is not None:
            query = query.filter(Expense.school_id == school_id)
        rows_data = query.order_by(Expense.expense_date).all()
        headers = ["Reference #", "Category", "Purpose", "Amount", "Paid To", "Date"]
        rows = [
            [e.reference_number, e.category_label, e.purpose, float(e.amount), e.paid_to or "", e.expense_date.isoformat()]
            for e in rows_data
        ]
        title = "Expense Report"
    else:
        headers, rows, title = [], [], "Report"

    subtitle = f"Period: {start_date.isoformat()} to {end_date.isoformat()}"

    if fmt == "csv":
        mem = export_csv(headers, rows)
        return send_file(mem, as_attachment=True, download_name=f"{report_type}_report.csv", mimetype="text/csv")
    elif fmt == "excel":
        mem = export_excel(headers, rows, sheet_title=title)
        return send_file(mem, as_attachment=True, download_name=f"{report_type}_report.xlsx",
                          mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif fmt == "pdf":
        mem = export_pdf_table(title, headers, rows, subtitle=subtitle)
        return send_file(mem, as_attachment=True, download_name=f"{report_type}_report.pdf", mimetype="application/pdf")

    return "Unsupported format", 400
