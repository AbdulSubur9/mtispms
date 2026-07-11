from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import Student, Payment, Expense, User, ClassRoom
from app.utils.helpers import scope_query_to_school

search_bp = Blueprint("search", __name__, template_folder="../templates/shared")


@search_bp.route("/")
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    results = {"students": [], "payments": [], "expenses": [], "collectors": [], "classes": []}

    if q:
        like = f"%{q}%"

        students_q = scope_query_to_school(Student.query, Student).filter(
            (Student.first_name.ilike(like)) | (Student.last_name.ilike(like))
            | (Student.student_id.ilike(like)) | (Student.guardian_name.ilike(like))
        )
        results["students"] = students_q.limit(15).all()

        payments_q = scope_query_to_school(Payment.query, Payment).filter(Payment.receipt_number.ilike(like))
        results["payments"] = payments_q.limit(15).all()

        expenses_q = scope_query_to_school(Expense.query, Expense).filter(
            (Expense.reference_number.ilike(like)) | (Expense.purpose.ilike(like))
        )
        results["expenses"] = expenses_q.limit(15).all()

        collectors_q = User.query.filter(
            (User.first_name.ilike(like)) | (User.last_name.ilike(like)) | (User.username.ilike(like))
        )
        results["collectors"] = collectors_q.limit(15).all()

        classes_q = scope_query_to_school(ClassRoom.query, ClassRoom).filter(ClassRoom.name.ilike(like))
        results["classes"] = classes_q.limit(15).all()

    return render_template("shared/search_results.html", q=q, results=results)
