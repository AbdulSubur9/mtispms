from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # null = broadcast to school

    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    category = db.Column(
        db.String(30), default="info"
    )  # upcoming_payment, outstanding_fee, expense_alert, payment_success, receipt_generated, info
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Notification {self.title}>"
