from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.fee_structures import fee_structures_bp
from app.fee_structures.forms import FeeStructureForm
from app.extensions import db
from app.models import FeeStructure, ClassRoom, AcademicYear, Term, SchoolPaymentType
from app.models.user import Role
from app.utils.helpers import current_school_id
from app.utils.db_safety import safe_commit

ADMIN_ROLES = (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)


def _populate_form_choices(form, school_id):
    form.class_id.choices = [(c.id, c.name) for c in ClassRoom.query.filter_by(school_id=school_id, is_active=True).order_by(ClassRoom.name).all()]
    form.academic_year_id.choices = [(y.id, y.name) for y in AcademicYear.query.filter_by(school_id=school_id, is_active=True).order_by(AcademicYear.start_date.desc()).all()]
    form.term_id.choices = [(t.id, t.name) for t in Term.query.filter_by(school_id=school_id, is_active=True).order_by(Term.start_date).all()]
    form.payment_type_id.choices = [(pt.id, pt.name) for pt in SchoolPaymentType.query.filter_by(school_id=school_id).order_by(SchoolPaymentType.name).all()]


@fee_structures_bp.route("/")
@login_required
def list_fee_structures():
    school_id = current_school_id()
    fees = FeeStructure.query.filter_by(school_id=school_id).order_by(FeeStructure.created_at.desc()).all()
    return render_template("fee_structures/list.html", fees=fees)


@fee_structures_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_fee_structure():
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    form = FeeStructureForm()
    _populate_form_choices(form, school_id)
    if form.validate_on_submit():
        fee = FeeStructure(
            school_id=school_id,
            class_id=form.class_id.data,
            academic_year_id=form.academic_year_id.data,
            term_id=form.term_id.data,
            payment_type_id=form.payment_type_id.data,
            amount=form.amount.data,
            due_date=form.due_date.data,
            is_mandatory=form.is_mandatory.data,
            is_active=form.is_active.data,
            notes=form.notes.data,
        )
        db.session.add(fee)
        if safe_commit():
            flash("Fee structure created.", "success")
            return redirect(url_for("fee_structures.list_fee_structures"))
    return render_template("fee_structures/form.html", form=form, title="Create Fee Structure")


@fee_structures_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_fee_structure(id):
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    fee = FeeStructure.query.filter_by(id=id, school_id=school_id).first_or_404()
    form = FeeStructureForm(obj=fee)
    _populate_form_choices(form, school_id)
    if form.validate_on_submit():
        fee.class_id = form.class_id.data
        fee.academic_year_id = form.academic_year_id.data
        fee.term_id = form.term_id.data
        fee.payment_type_id = form.payment_type_id.data
        fee.amount = form.amount.data
        fee.due_date = form.due_date.data
        fee.is_mandatory = form.is_mandatory.data
        fee.is_active = form.is_active.data
        fee.notes = form.notes.data
        if safe_commit():
            flash("Fee structure updated.", "success")
            return redirect(url_for("fee_structures.list_fee_structures"))
    return render_template("fee_structures/form.html", form=form, title="Edit Fee Structure", fee=fee)


@fee_structures_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_fee_structure(id):
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    fee = FeeStructure.query.filter_by(id=id, school_id=school_id).first_or_404()
    db.session.delete(fee)
    if safe_commit():
        flash("Fee structure deleted.", "success")
    return redirect(url_for("fee_structures.list_fee_structures"))
