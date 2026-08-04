from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ClassRoom, Student, Attendance, AuditLog
from app.models.user import Role
from app.models.attendance import AttendanceStatus
from app.utils.helpers import current_school_id, is_super_admin
from app.utils.db_safety import safe_commit

attendance_bp = Blueprint("attendance", __name__, template_folder="../templates/attendance")


def _teacher_classes():
    """Classes the current user is allowed to take attendance for: a Teacher
    sees only classes assigned to them; admins/accountants see every class in
    their school (useful for oversight, but they don't get a "My Classes"
    nav item - this route is reachable directly)."""
    query = ClassRoom.query
    if current_user.role == Role.TEACHER:
        query = query.filter(ClassRoom.teacher_id == current_user.id)
    elif not is_super_admin():
        query = query.filter(ClassRoom.school_id == current_school_id())
    return query.order_by(ClassRoom.name).all()


def _assert_can_manage_class(classroom):
    if not is_super_admin() and classroom.school_id != current_school_id():
        abort(403)
    if current_user.role == Role.TEACHER and classroom.teacher_id != current_user.id:
        abort(403)


@attendance_bp.route("/", methods=["GET", "POST"])
@login_required
def take_attendance():
    if current_user.role not in (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN, Role.TEACHER):
        abort(403)

    classes = _teacher_classes()
    class_id = request.args.get("class_id", type=int) or request.form.get("class_id", type=int)
    attendance_date_str = request.args.get("date") or request.form.get("date")
    attendance_date = (
        datetime.strptime(attendance_date_str, "%Y-%m-%d").date() if attendance_date_str else date.today()
    )

    classroom = None
    students = []
    existing = {}

    if class_id:
        classroom = ClassRoom.query.get_or_404(class_id)
        _assert_can_manage_class(classroom)
        students = classroom.students.filter_by(status="active").order_by(Student.first_name).all()
        existing = {
            a.student_id: a
            for a in Attendance.query.filter_by(class_id=class_id, attendance_date=attendance_date).all()
        }

    if request.method == "POST" and classroom:
        for student in students:
            status = request.form.get(f"status_{student.id}", AttendanceStatus.PRESENT)
            remarks = request.form.get(f"remarks_{student.id}", "")
            record = existing.get(student.id)
            if record:
                record.status = status
                record.remarks = remarks
                record.teacher_id = current_user.id
            else:
                record = Attendance(
                    school_id=classroom.school_id, class_id=classroom.id, student_id=student.id,
                    teacher_id=current_user.id, attendance_date=attendance_date, status=status, remarks=remarks,
                )
                db.session.add(record)

        if safe_commit(log_context=f"take_attendance class={class_id} date={attendance_date}"):
            AuditLog.log(
                "attendance_recorded", description=f"Attendance recorded for {classroom.name} on {attendance_date}",
                entity_type="class", entity_id=classroom.id, user=current_user,
            )
            flash("Attendance saved.", "success")
            return redirect(url_for("attendance.take_attendance", class_id=class_id, date=attendance_date.isoformat()))

    return render_template(
        "attendance/take.html", classes=classes, classroom=classroom, students=students,
        existing=existing, attendance_date=attendance_date, statuses=AttendanceStatus.ALL,
        status_labels=AttendanceStatus.LABELS,
    )


@attendance_bp.route("/reports")
@login_required
def reports():
    if current_user.role not in (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN, Role.TEACHER):
        abort(403)

    classes = _teacher_classes()
    class_id = request.args.get("class_id", type=int)
    period = request.args.get("period", "daily")
    today = date.today()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())
    elif period == "monthly":
        start = today.replace(day=1)
    else:
        start = today
    end = today

    records = []
    summary = {"present": 0, "absent": 0, "late": 0}
    classroom = None
    if class_id:
        classroom = ClassRoom.query.get_or_404(class_id)
        _assert_can_manage_class(classroom)
        records = (
            Attendance.query.filter(
                Attendance.class_id == class_id,
                Attendance.attendance_date >= start,
                Attendance.attendance_date <= end,
            )
            .order_by(Attendance.attendance_date.desc())
            .all()
        )
        for r in records:
            summary[r.status] = summary.get(r.status, 0) + 1

    return render_template(
        "attendance/reports.html", classes=classes, classroom=classroom, records=records,
        summary=summary, period=period, start=start, end=end,
    )
