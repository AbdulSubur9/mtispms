from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.academics import academics_bp
from app.academics.forms import AcademicYearForm, TermForm
from app.extensions import db
from app.models import AcademicYear, Term
from app.models.user import Role
from app.utils.helpers import current_school_id, is_super_admin
from app.utils.db_safety import safe_commit

ADMIN_ROLES = (Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)


@academics_bp.route("/years")
@login_required
def years_list():
    school_id = current_school_id()
    years = AcademicYear.query.filter_by(school_id=school_id).order_by(AcademicYear.start_date.desc()).all()
    return render_template("academics/years_list.html", years=years)


@academics_bp.route("/years/create", methods=["GET", "POST"])
@login_required
def year_create():
    if current_user.role not in ADMIN_ROLES:
        flash("You do not have permission to manage academic years.", "danger")
        return redirect(url_for("dashboard.index"))
    form = AcademicYearForm()
    if form.validate_on_submit():
        school_id = current_school_id()
        if form.is_current.data:
            AcademicYear.query.filter_by(school_id=school_id).update({"is_current": False})
        year = AcademicYear(
            school_id=school_id,
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_active=form.is_active.data,
            is_current=form.is_current.data,
        )
        db.session.add(year)
        if safe_commit():
            flash(f"Academic year '{year.name}' created.", "success")
            return redirect(url_for("academics.years_list"))
    return render_template("academics/year_form.html", form=form, title="Create Academic Year")


@academics_bp.route("/years/<int:id>/edit", methods=["GET", "POST"])
@login_required
def year_edit(id):
    if current_user.role not in ADMIN_ROLES:
        flash("You do not have permission.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    year = AcademicYear.query.filter_by(id=id, school_id=school_id).first_or_404()
    form = AcademicYearForm(obj=year)
    if form.validate_on_submit():
        if form.is_current.data:
            AcademicYear.query.filter_by(school_id=school_id).update({"is_current": False})
        year.name = form.name.data
        year.start_date = form.start_date.data
        year.end_date = form.end_date.data
        year.is_active = form.is_active.data
        year.is_current = form.is_current.data
        if safe_commit():
            flash("Academic year updated.", "success")
            return redirect(url_for("academics.years_list"))
    return render_template("academics/year_form.html", form=form, title="Edit Academic Year", year=year)


@academics_bp.route("/years/<int:id>/delete", methods=["POST"])
@login_required
def year_delete(id):
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    year = AcademicYear.query.filter_by(id=id, school_id=school_id).first_or_404()
    db.session.delete(year)
    if safe_commit():
        flash("Academic year deleted.", "success")
    return redirect(url_for("academics.years_list"))


@academics_bp.route("/years/<int:year_id>/terms")
@login_required
def terms_list(year_id):
    school_id = current_school_id()
    year = AcademicYear.query.filter_by(id=year_id, school_id=school_id).first_or_404()
    terms = Term.query.filter_by(academic_year_id=year.id).order_by(Term.start_date).all()
    return render_template("academics/terms_list.html", year=year, terms=terms)


@academics_bp.route("/years/<int:year_id>/terms/create", methods=["GET", "POST"])
@login_required
def term_create(year_id):
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    year = AcademicYear.query.filter_by(id=year_id, school_id=school_id).first_or_404()
    form = TermForm()
    if form.validate_on_submit():
        if form.is_current.data:
            Term.query.filter_by(school_id=school_id).update({"is_current": False})
        term = Term(
            academic_year_id=year.id,
            school_id=school_id,
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            is_active=form.is_active.data,
            is_current=form.is_current.data,
        )
        db.session.add(term)
        if safe_commit():
            flash(f"Term '{term.name}' created.", "success")
            return redirect(url_for("academics.terms_list", year_id=year.id))
    return render_template("academics/term_form.html", form=form, year=year, title="Create Term")


@academics_bp.route("/terms/<int:id>/edit", methods=["GET", "POST"])
@login_required
def term_edit(id):
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    term = Term.query.filter_by(id=id, school_id=school_id).first_or_404()
    form = TermForm(obj=term)
    if form.validate_on_submit():
        if form.is_current.data:
            Term.query.filter_by(school_id=school_id).update({"is_current": False})
        term.name = form.name.data
        term.start_date = form.start_date.data
        term.end_date = form.end_date.data
        term.is_active = form.is_active.data
        term.is_current = form.is_current.data
        if safe_commit():
            flash("Term updated.", "success")
            return redirect(url_for("academics.terms_list", year_id=term.academic_year_id))
    return render_template("academics/term_form.html", form=form, year=term.academic_year, title="Edit Term", term=term)


@academics_bp.route("/terms/<int:id>/delete", methods=["POST"])
@login_required
def term_delete(id):
    if current_user.role not in ADMIN_ROLES:
        flash("Permission denied.", "danger")
        return redirect(url_for("dashboard.index"))
    school_id = current_school_id()
    term = Term.query.filter_by(id=id, school_id=school_id).first_or_404()
    year_id = term.academic_year_id
    db.session.delete(term)
    if safe_commit():
        flash("Term deleted.", "success")
    return redirect(url_for("academics.terms_list", year_id=year_id))
