from datetime import datetime, date
from app.extensions import db


class PaymentType:
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

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    collector_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    receipt_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
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

    @property
    def payment_type_label(self):
        return PaymentType.LABELS.get(self.payment_type, self.payment_type)

    @staticmethod
    def generate_receipt_number(school_id):
        last = (
            Payment.query.filter_by(school_id=school_id)
            .order_by(Payment.id.desc())
            .first()
        )
        next_num = 1
        if last and last.receipt_number and "-" in last.receipt_number:
            try:
                next_num = int(last.receipt_number.split("-")[-1]) + 1
            except ValueError:
                next_num = Payment.query.filter_by(school_id=school_id).count() + 1
        year = datetime.utcnow().strftime("%y")
        return f"RCT-{year}-{next_num:05d}"

    def __repr__(self):
        return f"<Payment {self.receipt_number} {self.amount}>"
