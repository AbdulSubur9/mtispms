from datetime import datetime, date
from app.extensions import db


class PaymentType:
    """Legacy built-in payment type constants, retained as sensible defaults
    and for backward compatibility. Schools can additionally define their own
    custom payment types via the SchoolPaymentType model (see payment_type.py)."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    BUILDING_FUND = "building_fund"
    PTA_LEVY = "pta_levy"
    DONATION = "donation"

    ALL = [WEEKLY, MONTHLY, BUILDING_FUND, PTA_LEVY, DONATION]
    LABELS = {
        WEEKLY: "Weekly Payment",
        MONTHLY: "Monthly Contribution",
        BUILDING_FUND: "Building Fund",
        PTA_LEVY: "PTA Levy",
        DONATION: "Special Donation",
    }


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        # Receipt numbers are scoped per school - see Student.student_id note above
        # for why this must be a composite constraint rather than a bare global one.
        db.UniqueConstraint("school_id", "receipt_number", name="uq_payments_school_receipt_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    collector_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    payment_type_id = db.Column(db.Integer, db.ForeignKey("school_payment_types.id"), nullable=True)

    receipt_number = db.Column(db.String(30), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_type = db.Column(db.String(30), nullable=False, default=PaymentType.WEEKLY)
    payment_date = db.Column(db.Date, default=date.today, nullable=False)
    remarks = db.Column(db.String(250))

    is_void = db.Column(db.Boolean, default=False)
    voided_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    voided_at = db.Column(db.DateTime)
    void_reason = db.Column(db.String(250))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    voided_by = db.relationship("User", foreign_keys=[voided_by_id])
    custom_type = db.relationship("SchoolPaymentType", foreign_keys=[payment_type_id])

    @property
    def payment_type_label(self):
        if self.custom_type:
            return self.custom_type.name
        return PaymentType.LABELS.get(self.payment_type, self.payment_type)

    @staticmethod
    def generate_receipt_number(school_id):
        """Generate the next RCT-YY-NNNNN receipt number, unique within this
        school. Scans all of this school's receipt numbers for the current
        year rather than trusting the last-inserted row, so deletions/voids
        never cause a duplicate-key collision."""
        year = datetime.utcnow().strftime("%y")
        prefix = f"RCT-{year}-"
        existing = (
            db.session.query(Payment.receipt_number)
            .filter(Payment.school_id == school_id, Payment.receipt_number.like(f"{prefix}%"))
            .all()
        )
        max_num = 0
        for (rn,) in existing:
            try:
                num = int(rn.split("-")[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"{prefix}{max_num + 1:05d}"

    def __repr__(self):
        return f"<Payment {self.receipt_number} {self.amount}>"
