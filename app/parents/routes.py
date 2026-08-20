from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.parents import parents_bp
from app.extensions import db
from app.models import Parent, ParentStudent, Student, Result, Attendance, Payment, AcademicYear, Term, School
from app.models.user import Role
from app.utils.helpers import current_school_id
from app.services.results_service import compute_exam_summary


@parents_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != Role.PARENT:
        abort(403)
    parent = Parent.query.filter_by(user_id=current_user.id).first_or_404()
    children = [link.student for link in parent.parent_links]
    return render_template("parents/dashboard.html", parent=parent, children=children)


@parents_bp.route("/child/<int:student_id>")
@login_required
def child_detail(student_id):
    if current_user.role != Role.PARENT:
        abort(403)
    parent = Parent.query.filter_by(user_id=current_user.id).first_or_404()
    link = ParentStudent.query.filter_by(parent_id=parent.id, student_id=student_id).first()
    if not link:
        abort(403)
    student = Student.query.get_or_404(student_id)
    current_year = AcademicYear.query.filter_by(school_id=student.school_id, is_current=True).first()
    current_term = Term.query.filter_by(school_id=student.school_id, is_current=True).first()
    school = School.query.get(student.school_id)
    show_payments = bool(school and school.allow_parent_payment_view)
    return render_template(
        "parents/child_detail.html", student=student, current_year=current_year, current_term=current_term,
        show_payments=show_payments,
    )


@parents_bp.route("/child/<int:student_id>/results")
@login_required
def child_results(student_id):
    if current_user.role != Role.PARENT:
        abort(403)
    parent = Parent.query.filter_by(user_id=current_user.id).first_or_404()
    link = ParentStudent.query.filter_by(parent_id=parent.id, student_id=student_id).first()
    if not link:
        abort(403)
    student = Student.query.get_or_404(student_id)
    results = Result.query.filter_by(student_id=student.id).order_by(Result.created_at.desc()).all()
    summaries = {}
    for r in results:
        exam = r.exam_subject.exam
        if exam.id not in summaries:
            # compute_exam_summary(exam) needs the actual Exam object (not
            # its id) and returns a list of one row per student in the
            # class. Adapt that into the {student_id: row} lookup shape
            # this template expects - each row already has "grade",
            # "total", "percentage", "position" keys (Jinja's `.` operator
            # falls back to dict-key access, so `row.grade` /
            # `row["grade"]` are equivalent in the template below).
            rows = compute_exam_summary(exam)
            by_student = {row["student"].id: row for row in rows}
            summaries[exam.id] = {"grades": by_student, "students": by_student}
    return render_template("parents/child_results.html", student=student, results=results, summaries=summaries)


@parents_bp.route("/child/<int:student_id>/attendance")
@login_required
def child_attendance(student_id):
    if current_user.role != Role.PARENT:
        abort(403)
    parent = Parent.query.filter_by(user_id=current_user.id).first_or_404()
    link = ParentStudent.query.filter_by(parent_id=parent.id, student_id=student_id).first()
    if not link:
        abort(403)
    student = Student.query.get_or_404(student_id)
    records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.attendance_date.desc()).limit(90).all()
    total = len(records)
    present = sum(1 for r in records if r.status == "present")
    absent = sum(1 for r in records if r.status == "absent")
    excused = sum(1 for r in records if r.status == "excused")
    rate = round((present / total * 100), 1) if total else 0
    return render_template("parents/child_attendance.html", student=student, records=records, total=total, present=present, absent=absent, excused=excused, rate=rate)


@parents_bp.route("/child/<int:student_id>/payments")
@login_required
def child_payments(student_id):
    if current_user.role != Role.PARENT:
        abort(403)
    parent = Parent.query.filter_by(user_id=current_user.id).first_or_404()
    link = ParentStudent.query.filter_by(parent_id=parent.id, student_id=student_id).first()
    if not link:
        abort(403)
    student = Student.query.get_or_404(student_id)
    school = School.query.get(student.school_id)
    if school and not school.allow_parent_payment_view:
        flash("Payment information isn't available to parents for this school.", "info")
        return redirect(url_for("parents.child_detail", student_id=student.id))
    payments = Payment.query.filter_by(student_id=student.id, is_void=False).order_by(Payment.payment_date.desc()).all()
    total_paid = student.total_paid
    return render_template("parents/child_payments.html", student=student, payments=payments, total_paid=total_paid)
