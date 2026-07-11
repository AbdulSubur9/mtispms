from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ClassRoom, User, Student, AuditLog
from app.models.user import Role
from app.classes.forms import ClassRoomForm
from app.utils.decorators import write_access_required
from app.utils.helpers import scope_query_to_school, current_school_id, is_super_admin

classes_bp = Blueprint("classes", __name__, template_folder="../templates/classes")


def _populate_teacher_choices(form, school_id):
    q = User.query.filter(User.role.in_([Role.TEACHER, Role.SCHOOL_ADMIN]))
    if school_id is not None:
        q = q.filter_by(school_id=school_id)
    form.teacher_id.choices = [(0, "-- Unassigned --")] + [(u.id, u.full_name) for u in q.order_by(User.first_name).all()]


@classes_bp.route("/")
@login_required
def list_classes():
    query = scope_query_to_school(ClassRoom.query, ClassRoom)
    classes = query.order_by(ClassRoom.name).all()
    return render_template("classes/list.html", classes=classes)


@classes_bp.route("/<int:class_id>")
@login_required
def view_class(class_id):
    classroom = ClassRoom.query.get_or_404(class_id)
    if not is_super_admin() and classroom.school_id != current_school_id():
        abort(403)
    students = classroom.students.order_by(Student.first_name).all()
    return render_template("classes/view.html", classroom=classroom, students=students)


@classes_bp.route("/create", methods=["GET", "POST"])
@login_required
@write_access_required
def create_class():
    school_id = current_school_id()
    if school_id is None:
        flash("Select a school context first.", "warning")
        return redirect(url_for("classes.list_classes"))

    form = ClassRoomForm()
    _populate_teacher_choices(form, school_id)

    if form.validate_on_submit():
        classroom = ClassRoom(
            school_id=school_id,
            name=form.name.data.strip(),
            description=form.description.data,
            teacher_id=form.teacher_id.data or None,
        )
        db.session.add(classroom)
        db.session.commit()
        AuditLog.log(
            "class_created", description=f"Class {classroom.name} created", entity_type="class",
            entity_id=classroom.id, user=current_user,
        )
        flash("Class created successfully.", "success")
        return redirect(url_for("classes.list_classes"))

    return render_template("classes/form.html", form=form, title="Add Class")


@classes_bp.route("/<int:class_id>/edit", methods=["GET", "POST"])
@login_required
@write_access_required
def edit_class(class_id):
    classroom = ClassRoom.query.get_or_404(class_id)
    if not is_super_admin() and classroom.school_id != current_school_id():
        abort(403)

    form = ClassRoomForm(obj=classroom)
    _populate_teacher_choices(form, classroom.school_id)
    if request.method == "GET":
        form.teacher_id.data = classroom.teacher_id or 0

    if form.validate_on_submit():
        classroom.name = form.name.data.strip()
        classroom.description = form.description.data
        classroom.teacher_id = form.teacher_id.data or None
        db.session.commit()
        AuditLog.log(
            "class_updated", description=f"Class {classroom.name} updated", entity_type="class",
            entity_id=classroom.id, user=current_user,
        )
        flash("Class updated successfully.", "success")
        return redirect(url_for("classes.list_classes"))

    return render_template("classes/form.html", form=form, title="Edit Class", classroom=classroom)


@classes_bp.route("/<int:class_id>/delete", methods=["POST"])
@login_required
@write_access_required
def delete_class(class_id):
    classroom = ClassRoom.query.get_or_404(class_id)
    if not is_super_admin() and classroom.school_id != current_school_id():
        abort(403)
    if current_user.role not in (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN):
        abort(403)

    name = classroom.name
    db.session.delete(classroom)
    db.session.commit()
    AuditLog.log("class_deleted", description=f"Class {name} deleted", user=current_user)
    flash("Class deleted.", "info")
    return redirect(url_for("classes.list_classes"))


@classes_bp.route("/<int:class_id>/assign-students", methods=["POST"])
@login_required
@write_access_required
def assign_students(class_id):
    classroom = ClassRoom.query.get_or_404(class_id)
    if not is_super_admin() and classroom.school_id != current_school_id():
        abort(403)

    student_ids = request.form.getlist("student_ids")
    Student.query.filter(Student.id.in_(student_ids), Student.school_id == classroom.school_id).update(
        {"class_id": classroom.id}, synchronize_session=False
    )
    db.session.commit()
    AuditLog.log(
        "students_assigned_to_class", description=f"{len(student_ids)} students assigned to {classroom.name}",
        entity_type="class", entity_id=classroom.id, user=current_user,
    )
    flash("Students assigned to class.", "success")
    return redirect(url_for("classes.view_class", class_id=classroom.id))
