from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Payment, Student, AuditLog, Notification, Receipt, SchoolPaymentType
from app.models.user import Role
from app.payments.forms import PaymentForm, VoidPaymentForm
from app.utils.decorators import write_access_required, roles_required
from app.utils.helpers import scope_query_to_school, current_school_id, is_super_admin
from app.utils.db_safety import safe_commit
from app.services.export_service import generate_receipt_pdf

payments_bp = Blueprint("payments", __name__, template_folder="../templates/payments")


def _populate_student_choices(form, school_id):
    q = Student.query.filter_by(status="active")
    if school_id is not None:
        q = q.filter_by(school_id=school_id)
    form.student_id.choices = [(s.id, f"{s.student_id} - {s.full_name}") for s in q.order_by(Student.first_name).all()]


def _populate_custom_type_choices(form, school_id):
    q = SchoolPaymentType.query.filter_by(is_active=True)
    if school_id is not None:
        q = q.filter_by(school_id=school_id)
    form.custom_payment_type_id.choices = [(0, "-- None / Use standard type above --")] + [
        (t.id, f"{t.name} ({t.frequency_label})") for t in q.order_by(SchoolPaymentType.name).all()
    ]


def _quick_payment_types(school_id):
    """Active payment types with a default amount set, for the "quick
    amount" buttons on the payment form (section 8) - e.g. [ GH₵5.00 Weekly
    ] [ GH₵20.00 Monthly ]. Returned as plain dicts, JSON-serializable for
    the template's JS."""
    q = SchoolPaymentType.query.filter(SchoolPaymentType.is_active.is_(True), SchoolPaymentType.amount.isnot(None))
    if school_id is not None:
        q = q.filter_by(school_id=school_id)
    return [
        {
            "id": t.id, "name": t.name, "amount": float(t.amount),
            "allow_custom_amount": t.allow_custom_amount, "frequency": t.frequency_label,
        }
        for t in q.order_by(SchoolPaymentType.amount).all()
    ]


@payments_bp.route("/")
@login_required
def list_payments():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    payment_type = request.args.get("payment_type", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    query = scope_query_to_school(Payment.query, Payment)
    if current_user.role == Role.COLLECTOR:
        # Collectors only ever see the payments *they personally* collected,
        # not every payment across their school.
        query = query.filter(Payment.collector_id == current_user.id)

    if search:
        like = f"%{search}%"
        query = query.join(Student).filter(
            (Payment.receipt_number.ilike(like))
            | (Student.first_name.ilike(like))
            | (Student.last_name.ilike(like))
            | (Student.student_id.ilike(like))
        )
    if payment_type:
        query = query.filter(Payment.payment_type == payment_type)
    if start_date:
        query = query.filter(Payment.payment_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Payment.payment_date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    pagination = query.order_by(Payment.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    from app.models.payment import PaymentType
    return render_template(
        "payments/list.html", payments=pagination.items, pagination=pagination,
        search=search, payment_type=payment_type, start_date=start_date, end_date=end_date,
        payment_types=PaymentType.ALL, payment_type_labels=PaymentType.LABELS,
    )


@payments_bp.route("/collect")
@login_required
@write_access_required
def collect():
    """The fast payment-collection screen: live AJAX student search, then an
    inline payment form for whichever student the collector picks. Replaces
    having to scroll a long dropdown of every student in the school."""
    school_id = current_school_id()
    if school_id is None:
        flash("Select a school context first.", "warning")
        return redirect(url_for("payments.list_payments"))
    return render_template("payments/collect.html", school_id=school_id)


@payments_bp.route("/create", methods=["GET", "POST"])
@login_required
@write_access_required
def create_payment():
    school_id = current_school_id()
    if school_id is None:
        flash("Select a school context first.", "warning")
        return redirect(url_for("payments.list_payments"))

    form = PaymentForm()
    _populate_student_choices(form, school_id)
    _populate_custom_type_choices(form, school_id)
    quick_types = _quick_payment_types(school_id)

    preselected_student_id = request.args.get("student_id", type=int)
    if request.method == "GET":
        form.payment_date.data = date.today()
        if preselected_student_id:
            form.student_id.data = preselected_student_id

    if form.validate_on_submit():
        custom_type_id = form.custom_payment_type_id.data or None

        # Section 8: "Allow custom amount only where the user's role has
        # permission." A Collector using a payment type that has
        # allow_custom_amount=False must submit EXACTLY that type's amount -
        # enforced server-side, not just by disabling the input client-side,
        # since a disabled HTML field can still be edited via devtools.
        if custom_type_id and current_user.role == Role.COLLECTOR:
            selected_type = SchoolPaymentType.query.get(custom_type_id)
            if (
                selected_type and not selected_type.allow_custom_amount
                and selected_type.amount is not None
                and float(form.amount.data) != float(selected_type.amount)
            ):
                flash(
                    f"The amount for \"{selected_type.name}\" is fixed at GH₵{selected_type.amount:.2f} "
                    f"and can't be changed. Contact your School Admin if this needs to be different.",
                    "danger",
                )
                return render_template(
                    "payments/form.html", form=form, title="Record Payment", quick_types=quick_types
                )

        payment = Payment(
            school_id=school_id,
            student_id=form.student_id.data,
            collector_id=current_user.id,
            receipt_number=Payment.generate_receipt_number(school_id),
            amount=form.amount.data,
            payment_type=form.payment_type.data,
            payment_type_id=custom_type_id,
            payment_date=form.payment_date.data,
            remarks=form.remarks.data,
        )
        db.session.add(payment)

        if not safe_commit(log_context=f"create_payment school={school_id}"):
            return render_template("payments/form.html", form=form, title="Record Payment", quick_types=quick_types)

        db.session.add(
            Notification(
                school_id=school_id,
                title="Payment Received",
                message=f"Receipt {payment.receipt_number} for {payment.amount} recorded.",
                category="payment_success",
            )
        )
        safe_commit(log_context="payment notification")

        AuditLog.log(
            "payment_created", description=f"Payment {payment.receipt_number} recorded", entity_type="payment",
            entity_id=payment.id, user=current_user, school_id=school_id,
        )
        flash(f"Payment recorded. Receipt #{payment.receipt_number}", "success")
        return redirect(url_for("payments.view_receipt", payment_id=payment.id))

    return render_template("payments/form.html", form=form, title="Record Payment", quick_types=quick_types)


@payments_bp.route("/<int:payment_id>/receipt")
@login_required
def view_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if not is_super_admin() and payment.school_id != current_school_id():
        abort(403)
    return render_template("payments/receipt.html", payment=payment)


@payments_bp.route("/<int:payment_id>/receipt/pdf")
@login_required
def download_receipt_pdf(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if not is_super_admin() and payment.school_id != current_school_id():
        abort(403)
    mem = generate_receipt_pdf(payment.school, payment.student, payment, payment.collector)

    existing = Receipt.query.filter_by(payment_id=payment.id).first()
    if existing:
        existing.printed_count += 1
    else:
        db.session.add(Receipt(payment_id=payment.id, printed_count=1))
    safe_commit(log_context=f"receipt pdf {payment_id}")

    return send_file(mem, as_attachment=True, download_name=f"{payment.receipt_number}.pdf", mimetype="application/pdf")


@payments_bp.route("/<int:payment_id>/void", methods=["GET", "POST"])
@login_required
@roles_required(Role.SUPER_ADMIN, Role.SCHOOL_ADMIN)
def void_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if not is_super_admin() and payment.school_id != current_school_id():
        abort(403)

    form = VoidPaymentForm()
    if form.validate_on_submit():
        payment.is_void = True
        payment.voided_by_id = current_user.id
        payment.voided_at = datetime.utcnow()
        payment.void_reason = form.void_reason.data
        if safe_commit(log_context=f"void_payment {payment_id}"):
            AuditLog.log(
                "payment_deleted", description=f"Payment {payment.receipt_number} voided: {form.void_reason.data}",
                entity_type="payment", entity_id=payment.id, user=current_user,
            )
            flash("Payment voided.", "info")
            return redirect(url_for("payments.list_payments"))

    return render_template("payments/void.html", form=form, payment=payment)
