from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import School, User, AuditLog
from app.models.user import Role
from app.admin.forms import SchoolForm, UserForm
from app.utils.decorators import roles_required
from app.utils.helpers import current_school_id, is_super_admin

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
        db.session.commit()
        AuditLog.log("user_created", description=f"School {school.name} created", user=current_user)
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
        db.session.commit()
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
        query = query.filter_by(school_id=current_school_id())
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users_list.html", users=users)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def create_user():
    form = UserForm()
    form.school_id.choices = [(0, "-- None (Super Admin only) --")] + [
        (s.id, s.name) for s in School.query.order_by(School.name).all()
    ]
    if not is_super_admin():
        # school admins can only create users assigned to their own school, and can't create super admins
        form.role.choices = [(r, Role.LABELS[r]) for r in Role.ALL if r != Role.SUPER_ADMIN]

    if form.validate_on_submit():
        if not form.password.data:
            flash("Password is required when creating a new user.", "danger")
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
        db.session.commit()
        AuditLog.log(
            "user_created", description=f"User {user.username} ({user.role}) created", entity_type="user",
            entity_id=user.id, user=current_user,
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
    form.school_id.choices = [(0, "-- None (Super Admin only) --")] + [
        (s.id, s.name) for s in School.query.order_by(School.name).all()
    ]
    if not is_super_admin():
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
        db.session.commit()
        AuditLog.log(
            "user_created", description=f"User {user.username} updated", entity_type="user",
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
    user.is_active_user = not user.is_active_user
    db.session.commit()
    flash(f"User {'activated' if user.is_active_user else 'deactivated'}.", "info")
    return redirect(url_for("admin.list_users"))


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
