from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Expense, AuditLog, Notification
from app.models.user import Role
from app.models.expense import ExpenseCategory
from app.expenses.forms import ExpenseForm
from app.utils.decorators import roles_required
from app.utils.helpers import save_upload, scope_query_to_school, current_school_id, is_super_admin

expenses_bp = Blueprint("expenses", __name__, template_folder="../templates/expenses")

EXPENSE_MANAGERS = (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN, Role.ACCOUNTANT)


@expenses_bp.route("/")
@login_required
def list_expenses():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    query = scope_query_to_school(Expense.query, Expense)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Expense.reference_number.ilike(like)) | (Expense.purpose.ilike(like)) | (Expense.paid_to.ilike(like))
        )
    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        query = query.filter(Expense.expense_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Expense.expense_date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    pagination = query.order_by(Expense.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        "expenses/list.html", expenses=pagination.items, pagination=pagination,
        search=search, category=category, start_date=start_date, end_date=end_date,
        categories=ExpenseCategory.ALL, category_labels=ExpenseCategory.LABELS,
    )


@expenses_bp.route("/create", methods=["GET", "POST"])
@login_required
@roles_required(*EXPENSE_MANAGERS)
def create_expense():
    school_id = current_school_id()
    if school_id is None:
        flash("Select a school context first.", "warning")
        return redirect(url_for("expenses.list_expenses"))

    form = ExpenseForm()
    if request.method == "GET":
        form.expense_date.data = date.today()

    if form.validate_on_submit():
        receipt_path = save_upload(form.receipt_file.data, subfolder="expenses") if form.receipt_file.data else None
        expense = Expense(
            school_id=school_id,
            reference_number=Expense.generate_reference_number(school_id),
            amount=form.amount.data,
            purpose=form.purpose.data.strip(),
            category=form.category.data,
            paid_to=form.paid_to.data,
            approved_by=form.approved_by.data,
            recorded_by_id=current_user.id,
            receipt_file=receipt_path,
            expense_date=form.expense_date.data,
            remarks=form.remarks.data,
        )
        db.session.add(expense)
        db.session.commit()

        db.session.add(
            Notification(
                school_id=school_id,
                title="Expense Recorded",
                message=f"{expense.reference_number}: {expense.amount} for {expense.purpose}",
                category="expense_alert",
            )
        )
        db.session.commit()

        AuditLog.log(
            "expense_recorded", description=f"Expense {expense.reference_number} recorded", entity_type="expense",
            entity_id=expense.id, user=current_user, school_id=school_id,
        )
        flash(f"Expense recorded. Reference #{expense.reference_number}", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/form.html", form=form, title="Record Expense")


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(*EXPENSE_MANAGERS)
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if not is_super_admin() and expense.school_id != current_school_id():
        abort(403)

    form = ExpenseForm(obj=expense)
    if form.validate_on_submit():
        expense.amount = form.amount.data
        expense.purpose = form.purpose.data.strip()
        expense.category = form.category.data
        expense.paid_to = form.paid_to.data
        expense.approved_by = form.approved_by.data
        expense.expense_date = form.expense_date.data
        expense.remarks = form.remarks.data
        if form.receipt_file.data:
            expense.receipt_file = save_upload(form.receipt_file.data, subfolder="expenses")
        db.session.commit()
        AuditLog.log(
            "expense_edited", description=f"Expense {expense.reference_number} edited", entity_type="expense",
            entity_id=expense.id, user=current_user,
        )
        flash("Expense updated.", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/form.html", form=form, title="Edit Expense", expense=expense)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if not is_super_admin() and expense.school_id != current_school_id():
        abort(403)

    ref = expense.reference_number
    db.session.delete(expense)
    db.session.commit()
    AuditLog.log("expense_deleted", description=f"Expense {ref} deleted", user=current_user)
    flash("Expense deleted.", "info")
    return redirect(url_for("expenses.list_expenses"))
