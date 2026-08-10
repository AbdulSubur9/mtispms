from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import StudentApplication, Student, AuditLog
from app.models.user import Role
from app.models.student_application import ApplicationStatus
from app.applications.forms import StudentApplicationForm
from app.utils.decorators import roles_required
from app.utils.helpers import current_school_id, is_super_admin
from app.utils.db_safety import safe_commit
from app.services.export_service import generate_application_pdf

applications_bp = Blueprint("applications", __name__, template_folder="../templates/applications")


@applications_bp.route("/")
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def list_applications():
    school_id = current_school_id()
    query = StudentApplication.query
    if school_id is not None:
        query = query.filter_by(school_id=school_id)
    applications = query.order_by(StudentApplication.created_at.desc()).all()
    return render_template("applications/list.html", applications=applications)


@applications_bp.route("/create", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def create_application():
    school_id = current_school_id()
    if school_id is None:
        flash("Select a school context first.", "warning")
        return redirect(url_for("applications.list_applications"))

    form = StudentApplicationForm()
    if form.validate_on_submit():
        application = StudentApplication(
            school_id=school_id,
            full_name=form.full_name.data.strip(),
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            previous_school=form.previous_school.data,
            address=form.address.data,
            guardian_name=form.guardian_name.data.strip(),
            guardian_phone=form.guardian_phone.data.strip(),
            guardian_occupation=form.guardian_occupation.data,
            guardian_address=form.guardian_address.data,
            emergency_contact_name=form.emergency_contact_name.data,
            emergency_contact_phone=form.emergency_contact_phone.data,
            emergency_contact_relationship=form.emergency_contact_relationship.data,
            has_medical_condition=form.has_medical_condition.data,
            medical_condition_details=form.medical_condition_details.data if form.has_medical_condition.data else None,
            declaration_accepted=form.declaration_accepted.data,
            submitted_by_id=current_user.id,
            application_date=date.today(),
        )
        db.session.add(application)
        if safe_commit(log_context=f"create_application school={school_id}"):
            AuditLog.log(
                "application_submitted", description=f"Application for {application.full_name} submitted",
                entity_type="application", entity_id=application.id, user=current_user, school_id=school_id,
            )
            flash("Application submitted.", "success")
            return redirect(url_for("applications.list_applications"))

    return render_template("applications/form.html", form=form, title="New Student Application")


@applications_bp.route("/<int:application_id>")
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def view_application(application_id):
    application = StudentApplication.query.get_or_404(application_id)
    if not is_super_admin() and application.school_id != current_school_id():
        abort(403)
    return render_template("applications/view.html", application=application)


@applications_bp.route("/<int:application_id>/pdf")
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def download_application_pdf(application_id):
    application = StudentApplication.query.get_or_404(application_id)
    if not is_super_admin() and application.school_id != current_school_id():
        abort(403)
    mem = generate_application_pdf(application.school, application)
    return send_file(
        mem, as_attachment=True, download_name=f"application_{application.id}.pdf", mimetype="application/pdf"
    )


@applications_bp.route("/<int:application_id>/approve", methods=["POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def approve_application(application_id):
    application = StudentApplication.query.get_or_404(application_id)
    if not is_super_admin() and application.school_id != current_school_id():
        abort(403)

    student = Student(
        school_id=application.school_id,
        student_id=Student.generate_student_id(application.school_id),
        first_name=application.full_name.split(" ")[0],
        last_name=" ".join(application.full_name.split(" ")[1:]) or application.full_name,
        gender=application.gender,
        date_of_birth=application.date_of_birth,
        guardian_name=application.guardian_name,
        guardian_contact=application.guardian_phone,
        admission_date=date.today(),
        status="active",
    )
    db.session.add(student)
    db.session.flush()
    application.status = ApplicationStatus.APPROVED
    application.student_id = student.id

    if safe_commit(log_context=f"approve_application {application_id}"):
        AuditLog.log(
            "application_approved", description=f"Application for {application.full_name} approved and admitted as {student.student_id}",
            entity_type="application", entity_id=application.id, user=current_user,
        )
        flash(f"Application approved. Student record {student.student_id} created.", "success")
    return redirect(url_for("applications.view_application", application_id=application.id))


@applications_bp.route("/<int:application_id>/reject", methods=["POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def reject_application(application_id):
    application = StudentApplication.query.get_or_404(application_id)
    if not is_super_admin() and application.school_id != current_school_id():
        abort(403)
    application.status = ApplicationStatus.REJECTED
    if safe_commit(log_context=f"reject_application {application_id}"):
        AuditLog.log(
            "application_rejected", description=f"Application for {application.full_name} rejected",
            entity_type="application", entity_id=application.id, user=current_user,
        )
        flash("Application rejected.", "info")
    return redirect(url_for("applications.view_application", application_id=application.id))
