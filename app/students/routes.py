from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort
from flask_login import login_required, current_user
from openpyxl import load_workbook
from app.extensions import db
from app.models import Student, ClassRoom, AuditLog, Payment
from app.models.user import Role
from app.students.forms import StudentForm, StudentUploadForm
from app.utils.decorators import write_access_required
from app.utils.helpers import save_upload, scope_query_to_school, current_school_id, is_super_admin
from app.services.export_service import export_excel

students_bp = Blueprint("students", __name__, template_folder="../templates/students")


def _populate_class_choices(form, school_id):
    q = ClassRoom.query
    if school_id is not None:
        q = q.filter_by(school_id=school_id)
    form.class_id.choices = [(0, "-- No Class --")] + [(c.id, c.name) for c in q.order_by(ClassRoom.name).all()]


@students_bp.route("/")
@login_required
def list_students():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    class_id = request.args.get("class_id", type=int)

    query = scope_query_to_school(Student.query, Student)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Student.first_name.ilike(like))
            | (Student.last_name.ilike(like))
            | (Student.student_id.ilike(like))
            | (Student.guardian_name.ilike(like))
        )
    if status:
        query = query.filter(Student.status == status)
    if class_id:
        query = query.filter(Student.class_id == class_id)

    pagination = query.order_by(Student.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    classes_q = ClassRoom.query
    if not is_super_admin():
        classes_q = classes_q.filter_by(school_id=current_school_id())
    classes = classes_q.order_by(ClassRoom.name).all()

    return render_template(
        "students/list.html", students=pagination.items, pagination=pagination,
        search=search, status=status, class_id=class_id, classes=classes,
    )


@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    student = Student.query.get_or_404(student_id)
    if not is_super_admin() and student.school_id != current_school_id():
        abort(403)
    payments = student.payments.order_by(Payment.payment_date.desc()).limit(50).all()
    return render_template("students/view.html", student=student, payments=payments)


@students_bp.route("/create", methods=["GET", "POST"])
@login_required
@write_access_required
def create_student():
    school_id = current_school_id() if not is_super_admin() else request.args.get("school_id", type=int)
    if school_id is None:
        flash("Select a school context before adding a student.", "warning")
        return redirect(url_for("dashboard.index"))

    form = StudentForm()
    _populate_class_choices(form, school_id)

    if form.validate_on_submit():
        photo_path = save_upload(form.photo.data, subfolder="students") if form.photo.data else None
        student = Student(
            school_id=school_id,
            student_id=Student.generate_student_id(school_id),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            guardian_name=form.guardian_name.data.strip(),
            guardian_contact=form.guardian_contact.data.strip(),
            class_id=form.class_id.data or None,
            admission_date=form.admission_date.data or date.today(),
            status=form.status.data,
            photo=photo_path,
        )
        db.session.add(student)
        db.session.commit()
        AuditLog.log(
            "student_created", description=f"Student {student.student_id} created", entity_type="student",
            entity_id=student.id, user=current_user, school_id=school_id,
        )
        flash(f"Student {student.full_name} ({student.student_id}) created successfully.", "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/form.html", form=form, title="Add Student")


@students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@write_access_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if not is_super_admin() and student.school_id != current_school_id():
        abort(403)

    form = StudentForm(obj=student)
    _populate_class_choices(form, student.school_id)
    if request.method == "GET":
        form.class_id.data = student.class_id or 0

    if form.validate_on_submit():
        student.first_name = form.first_name.data.strip()
        student.last_name = form.last_name.data.strip()
        student.gender = form.gender.data
        student.date_of_birth = form.date_of_birth.data
        student.guardian_name = form.guardian_name.data.strip()
        student.guardian_contact = form.guardian_contact.data.strip()
        student.class_id = form.class_id.data or None
        student.admission_date = form.admission_date.data
        student.status = form.status.data
        if form.photo.data:
            student.photo = save_upload(form.photo.data, subfolder="students")
        db.session.commit()
        AuditLog.log(
            "student_updated", description=f"Student {student.student_id} updated", entity_type="student",
            entity_id=student.id, user=current_user,
        )
        flash("Student updated successfully.", "success")
        return redirect(url_for("students.view_student", student_id=student.id))

    return render_template("students/form.html", form=form, title="Edit Student", student=student)


@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
@write_access_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    if not is_super_admin() and student.school_id != current_school_id():
        abort(403)
    if current_user.role not in (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN):
        abort(403)

    student_ref = f"{student.student_id} - {student.full_name}"
    db.session.delete(student)
    db.session.commit()
    AuditLog.log("student_deleted", description=f"Student {student_ref} deleted", user=current_user)
    flash("Student deleted.", "info")
    return redirect(url_for("students.list_students"))


@students_bp.route("/<int:student_id>/deactivate", methods=["POST"])
@login_required
@write_access_required
def deactivate_student(student_id):
    student = Student.query.get_or_404(student_id)
    if not is_super_admin() and student.school_id != current_school_id():
        abort(403)
    student.status = "deactivated"
    db.session.commit()
    AuditLog.log(
        "student_deactivated", description=f"Student {student.student_id} deactivated",
        entity_type="student", entity_id=student.id, user=current_user,
    )
    flash("Student deactivated.", "info")
    return redirect(url_for("students.view_student", student_id=student.id))


@students_bp.route("/upload", methods=["GET", "POST"])
@login_required
@write_access_required
def upload_students():
    school_id = current_school_id()
    if school_id is None and not is_super_admin():
        flash("No school context found.", "warning")
        return redirect(url_for("students.list_students"))

    form = StudentUploadForm()
    if form.validate_on_submit():
        wb = load_workbook(form.file.data, data_only=True)
        ws = wb.active
        created = 0
        errors = []
        header = [str(c.value).strip().lower() if c.value else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]

        required_cols = {"first_name", "last_name"}
        if not required_cols.issubset(set(header)):
            flash("Excel file must contain at least 'first_name' and 'last_name' columns.", "danger")
            return redirect(url_for("students.upload_students"))

        col_index = {name: idx for idx, name in enumerate(header)}

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[col_index.get("first_name", 0)]:
                continue
            try:
                first_name = str(row[col_index["first_name"]]).strip()
                last_name = str(row[col_index.get("last_name", 1)]).strip()
                gender = str(row[col_index["gender"]]).strip().lower() if "gender" in col_index and row[col_index["gender"]] else "male"
                guardian_name = str(row[col_index["guardian_name"]]).strip() if "guardian_name" in col_index and row[col_index["guardian_name"]] else ""
                guardian_contact = str(row[col_index["guardian_contact"]]).strip() if "guardian_contact" in col_index and row[col_index["guardian_contact"]] else ""

                student = Student(
                    school_id=school_id,
                    student_id=Student.generate_student_id(school_id),
                    first_name=first_name,
                    last_name=last_name,
                    gender=gender,
                    guardian_name=guardian_name,
                    guardian_contact=guardian_contact,
                    admission_date=date.today(),
                    status="active",
                )
                db.session.add(student)
                db.session.flush()
                created += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))

        db.session.commit()
        AuditLog.log(
            "students_bulk_uploaded", description=f"{created} students uploaded via Excel",
            user=current_user, school_id=school_id,
        )
        flash(f"{created} students imported successfully." + (f" {len(errors)} rows skipped." if errors else ""), "success")
        return redirect(url_for("students.list_students"))

    return render_template("students/upload.html", form=form)


@students_bp.route("/download")
@login_required
def download_students():
    query = scope_query_to_school(Student.query, Student)
    students = query.order_by(Student.student_id).all()
    headers = ["Student ID", "First Name", "Last Name", "Gender", "Guardian", "Guardian Contact", "Class", "Status", "Admission Date"]
    rows = [
        [
            s.student_id, s.first_name, s.last_name, s.gender, s.guardian_name, s.guardian_contact,
            s.classroom.name if s.classroom else "", s.status, s.admission_date.isoformat() if s.admission_date else "",
        ]
        for s in students
    ]
    mem = export_excel(headers, rows, sheet_title="Students")
    return send_file(mem, as_attachment=True, download_name="students.xlsx",
                      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
