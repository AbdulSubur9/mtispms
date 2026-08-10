from datetime import datetime
from app.extensions import db


class PaymentFrequency:
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TERMLY = "termly"
    YEARLY = "yearly"
    ONE_OFF = "one_off"

    ALL = [WEEKLY, MONTHLY, TERMLY, YEARLY, ONE_OFF]
    LABELS = {
        WEEKLY: "Weekly",
        MONTHLY: "Monthly",
        TERMLY: "Termly",
        YEARLY: "Yearly",
        ONE_OFF: "One-off",
    }


class SchoolPaymentType(db.Model):
    """Lets each school define its own payment structures (e.g. 'Saturday
    Payment', 'First Term Fees') instead of being limited to the built-in
    PaymentType constants. Payments can optionally reference one of these
    via Payment.payment_type_id; the legacy `payment_type` string column is
    kept for backward compatibility and simple categorisation/reporting."""
    __tablename__ = "school_payment_types"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_school_payment_types_school_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(20), nullable=False, default=PaymentFrequency.WEEKLY)
    amount = db.Column(db.Numeric(12, 2), nullable=True)  # suggested/default amount; collectors can still override
    # When False, Collectors must use `amount` as-is (no free-typing a
    # different number) - prevents accidental mis-keyed amounts for
    # standard fees. School Admin/Super Admin/Accountant can always
    # override regardless, since they're more trusted roles.
    allow_custom_amount = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(250))
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school = db.relationship("School", foreign_keys=[school_id])

    @property
    def frequency_label(self):
        return PaymentFrequency.LABELS.get(self.frequency, self.frequency)

    def __repr__(self):
        return f"<SchoolPaymentType {self.name} ({self.school_id})>"
