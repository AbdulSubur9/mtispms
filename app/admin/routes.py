from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import School, User, AuditLog, SchoolPaymentType
from app.models.user import Role
from app.admin.forms import SchoolForm, UserForm, PaymentTypeForm
from app.utils.decorators import roles_required
from app.utils.helpers import current_school_id, is_super_admin
from app.utils.db_safety import safe_commit

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


# ---------- Schools (Super Admin only) ----------

@admin_bp.route("/schools")
@login_required
@roles_required(Role.SUPER_ADMIN)
def list_schools():
    schools = School.query.order_by(School.name).all()
    return render_template("admin/schools_list.html", schools=schools)


@admin_bp.route("/schools/create", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN)
def create_school():
    form = SchoolForm()
    if form.validate_on_submit():
        school = School(
            name=form.name.data.strip(), code=form.code.data.strip().upper(),
            address=form.address.data, phone=form.phone.data, email=form.email.data,
            is_active=form.is_active.data,
        )
        db.session.add(school)
        if safe_commit(log_context=f"create_school by user {current_user.id}"):
            AuditLog.log("school_created", description=f"School {school.name} created", user=current_user)
            flash("School created successfully.", "success")
            return redirect(url_for("admin.list_schools"))
    return render_template("admin/school_form.html", form=form, title="Add School")


@admin_bp.route("/schools/<int:school_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN)
def edit_school(school_id):
    school = School.query.get_or_404(school_id)
    form = SchoolForm(obj=school)
    if form.validate_on_submit():
        school.name = form.name.data.strip()
        school.code = form.code.data.strip().upper()
        school.address = form.address.data
        school.phone = form.phone.data
        school.email = form.email.data
        school.is_active = form.is_active.data
        if safe_commit(log_context=f"edit_school {school.id}"):
            flash("School updated.", "success")
            return redirect(url_for("admin.list_schools"))
    return render_template("admin/school_form.html", form=form, title="Edit School", school=school)


# ---------- Users ----------

@admin_bp.route("/users")
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def list_users():
    query = User.query
    if not is_super_admin():
        # Strict multi-tenant isolation: a School Admin only ever sees users
        # belonging to their own school.
        query = query.filter_by(school_id=current_school_id())
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users_list.html", users=users)


def _school_choices():
    return [(0, "-- Select a School --")] + [(s.id, s.name) for s in School.query.order_by(School.name).all()]


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def create_user():
    form = UserForm()

    if is_super_admin():
        form.school_id.choices = _school_choices()
    else:
        # School Admins may only ever create users inside their own school -
        # lock the dropdown to a single option so it can never be tampered
        # with client-side to assign a user to a different tenant.
        form.school_id.choices = [(current_school_id(), current_user.school.name)]
        form.school_id.data = current_school_id()
        form.role.choices = [(r, Role.LABELS[r]) for r in Role.ALL if r != Role.SUPER_ADMIN]

    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required when creating a new user.")
            return render_template("admin/user_form.html", form=form, title="Add User")

        school_id = form.school_id.data or None
        if not is_super_admin():
            school_id = current_school_id()
            if form.role.data == Role.SUPER_ADMIN:
                abort(403)

        user = User(
            username=form.username.data.strip(), email=form.email.data.strip().lower(),
            first_name=form.first_name.data.strip(), last_name=form.last_name.data.strip(),
            phone=form.phone.data, role=form.role.data, school_id=school_id,
            is_active_user=form.is_active_user.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        if safe_commit(log_context=f"create_user by user {current_user.id}"):
            AuditLog.log(
                "user_created", description=f"User {user.username} ({user.role}) created", entity_type="user",
                entity_id=user.id, user=current_user, school_id=school_id,
            )
            flash(f"User {user.full_name} created successfully.", "success")
            return redirect(url_for("admin.list_users"))

    return render_template("admin/user_form.html", form=form, title="Add User")


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if not is_super_admin() and user.school_id != current_school_id():
        abort(403)

    form = UserForm(obj=user)
    if is_super_admin():
        form.school_id.choices = _school_choices()
    else:
        form.school_id.choices = [(current_school_id(), current_user.school.name)]
        form.role.choices = [(r, Role.LABELS[r]) for r in Role.ALL if r != Role.SUPER_ADMIN]

    if request.method == "GET":
        form.school_id.data = user.school_id or 0
        form.password.data = ""

    if form.validate_on_submit():
        user.username = form.username.data.strip()
        user.email = form.email.data.strip().lower()
        user.first_name = form.first_name.data.strip()
        user.last_name = form.last_name.data.strip()
        user.phone = form.phone.data
        user.role = form.role.data
        user.is_active_user = form.is_active_user.data
        if is_super_admin():
            user.school_id = form.school_id.data or None
        if form.password.data:
            user.set_password(form.password.data)
        if safe_commit(log_context=f"edit_user {user.id}"):
            AuditLog.log(
                "user_updated", description=f"User {user.username} updated", entity_type="user",
                entity_id=user.id, user=current_user,
            )
            flash("User updated successfully.", "success")
            return redirect(url_for("admin.list_users"))

    return render_template("admin/user_form.html", form=form, title="Edit User", edit_user_obj=user)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if not is_super_admin() and user.school_id != current_school_id():
        abort(403)
    if user.id == current_user.id:
        flash("You can't deactivate your own account.", "warning")
        return redirect(url_for("admin.list_users"))

    user.is_active_user = not user.is_active_user
    if safe_commit(log_context=f"toggle_user_active {user.id}"):
        AuditLog.log(
            "user_updated", description=f"User {user.username} {'activated' if user.is_active_user else 'deactivated'}",
            entity_type="user", entity_id=user.id, user=current_user,
        )
        flash(f"User {'activated' if user.is_active_user else 'deactivated'}.", "info")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if not is_super_admin() and user.school_id != current_school_id():
        abort(403)
    if user.id == current_user.id:
        flash("You can't delete your own account.", "warning")
        return redirect(url_for("admin.list_users"))
    if user.role == Role.SUPER_ADMIN and not is_super_admin():
        abort(403)

    username = user.username
    db.session.delete(user)
    if safe_commit(
        friendly_message="This user can't be deleted because they have existing payments, expenses, "
                          "or other records linked to them. Deactivate the account instead.",
        log_context=f"delete_user {user_id}",
    ):
        AuditLog.log("user_deleted", description=f"User {username} deleted", user=current_user)
        flash("User deleted.", "info")
    return redirect(url_for("admin.list_users"))


# ---------- Payment Types (Settings) ----------

@admin_bp.route("/payment-types")
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def list_payment_types():
    school_id = current_school_id()
    query = SchoolPaymentType.query
    if school_id is not None:
        query = query.filter_by(school_id=school_id)
    elif not is_super_admin():
        query = query.filter(SchoolPaymentType.school_id.is_(None))  # will yield nothing; forces school selection
    types = query.order_by(SchoolPaymentType.name).all()
    return render_template(
        "admin/payment_types_list.html", payment_types=types,
        schools=School.query.order_by(School.name).all() if is_super_admin() else [],
        selected_school_id=school_id,
    )


@admin_bp.route("/payment-types/create", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def create_payment_type():
    school_id = current_school_id()
    if school_id is None:
        flash("Select a school first.", "warning")
        return redirect(url_for("admin.list_payment_types"))

    form = PaymentTypeForm()
    if form.validate_on_submit():
        pt = SchoolPaymentType(
            school_id=school_id, name=form.name.data.strip(), frequency=form.frequency.data,
            amount=form.amount.data, description=form.description.data, is_active=form.is_active.data,
        )
        db.session.add(pt)
        if safe_commit(
            friendly_message="A payment type with this name already exists for this school.",
            log_context=f"create_payment_type school={school_id}",
        ):
            flash("Payment type created.", "success")
            return redirect(url_for("admin.list_payment_types", school_id=school_id))
    return render_template("admin/payment_type_form.html", form=form, title="Add Payment Type")


@admin_bp.route("/payment-types/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def edit_payment_type(type_id):
    pt = SchoolPaymentType.query.get_or_404(type_id)
    if not is_super_admin() and pt.school_id != current_school_id():
        abort(403)

    form = PaymentTypeForm(obj=pt)
    if form.validate_on_submit():
        pt.name = form.name.data.strip()
        pt.frequency = form.frequency.data
        pt.amount = form.amount.data
        pt.description = form.description.data
        pt.is_active = form.is_active.data
        if safe_commit(
            friendly_message="A payment type with this name already exists for this school.",
            log_context=f"edit_payment_type {type_id}",
        ):
            flash("Payment type updated.", "success")
            return redirect(url_for("admin.list_payment_types"))
    return render_template("admin/payment_type_form.html", form=form, title="Edit Payment Type")


@admin_bp.route("/payment-types/<int:type_id>/delete", methods=["POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def delete_payment_type(type_id):
    pt = SchoolPaymentType.query.get_or_404(type_id)
    if not is_super_admin() and pt.school_id != current_school_id():
        abort(403)
    pt.is_active = False  # soft-delete: keep history for past payments that reference it
    if safe_commit(log_context=f"delete_payment_type {type_id}"):
        flash("Payment type deactivated.", "info")
    return redirect(url_for("admin.list_payment_types"))


# ---------- Audit Log ----------

@admin_bp.route("/audit-log")
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def audit_log():
    page = request.args.get("page", 1, type=int)
    query = AuditLog.query
    if not is_super_admin():
        query = query.filter_by(school_id=current_school_id())
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template("admin/audit_log.html", logs=pagination.items, pagination=pagination)
