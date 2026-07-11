from datetime import date
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user, login_user, logout_user
from app.extensions import db, csrf
from app.models import Student, Payment, Expense, User
from app.services import stats_service as stats
from app.utils.helpers import scope_query_to_school, current_school_id

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _paginate(query, schema_fn):
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [schema_fn(x) for x in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


# ---------- Auth ----------

@api_bp.route("/auth/login", methods=["POST"])
@csrf.exempt
def api_login():
    data = request.get_json(silent=True) or {}
    user = User.query.filter(
        (User.username == data.get("username")) | (User.email == data.get("username"))
    ).first()
    if not user or not user.check_password(data.get("password", "")):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active_user:
        return jsonify({"error": "Account deactivated"}), 403
    login_user(user)
    return jsonify({"message": "Logged in", "user": {"id": user.id, "username": user.username, "role": user.role}})


@api_bp.route("/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "Logged out"})


# ---------- Students ----------

def _student_schema(s):
    return {
        "id": s.id, "student_id": s.student_id, "first_name": s.first_name, "last_name": s.last_name,
        "gender": s.gender, "guardian_name": s.guardian_name, "guardian_contact": s.guardian_contact,
        "class_id": s.class_id, "status": s.status,
        "admission_date": s.admission_date.isoformat() if s.admission_date else None,
    }


@api_bp.route("/students", methods=["GET"])
@login_required
def api_list_students():
    query = scope_query_to_school(Student.query, Student)
    return _paginate(query.order_by(Student.id.desc()), _student_schema)


@api_bp.route("/students/<int:student_id>", methods=["GET"])
@login_required
def api_get_student(student_id):
    s = Student.query.get_or_404(student_id)
    return jsonify(_student_schema(s))


# ---------- Payments ----------

def _payment_schema(p):
    return {
        "id": p.id, "receipt_number": p.receipt_number, "student_id": p.student_id,
        "amount": float(p.amount), "payment_type": p.payment_type,
        "payment_date": p.payment_date.isoformat(), "is_void": p.is_void,
    }


@api_bp.route("/payments", methods=["GET"])
@login_required
def api_list_payments():
    query = scope_query_to_school(Payment.query, Payment)
    return _paginate(query.order_by(Payment.id.desc()), _payment_schema)


@api_bp.route("/payments/<int:payment_id>", methods=["GET"])
@login_required
def api_get_payment(payment_id):
    p = Payment.query.get_or_404(payment_id)
    return jsonify(_payment_schema(p))


# ---------- Expenses ----------

def _expense_schema(e):
    return {
        "id": e.id, "reference_number": e.reference_number, "amount": float(e.amount),
        "category": e.category, "purpose": e.purpose, "expense_date": e.expense_date.isoformat(),
    }


@api_bp.route("/expenses", methods=["GET"])
@login_required
def api_list_expenses():
    query = scope_query_to_school(Expense.query, Expense)
    return _paginate(query.order_by(Expense.id.desc()), _expense_schema)


# ---------- Dashboard / Reports ----------

@api_bp.route("/dashboard/summary", methods=["GET"])
@login_required
def api_dashboard_summary():
    school_id = current_school_id()
    today = date.today()
    month_start = today.replace(day=1)
    return jsonify({
        "total_students": stats.total_students(school_id),
        "today_collections": stats.collections_between(school_id, today, today),
        "monthly_collections": stats.collections_between(school_id, month_start, today),
        "total_income": stats.total_income(school_id),
        "total_expenses": stats.total_expenses(school_id),
        "current_balance": stats.current_balance(school_id),
    })


@api_bp.route("/reports/income", methods=["GET"])
@login_required
def api_income_report():
    school_id = current_school_id()
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    from datetime import datetime
    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else date.today().replace(day=1)
    end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    return jsonify({
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_income": stats.collections_between(school_id, start_date, end_date),
    })
