from datetime import datetime
from app.extensions import db


class Receipt(db.Model):
    """Stores generated printable receipt metadata (PDF path/history) for a payment."""
    __tablename__ = "receipts"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=False, unique=True)
    file_path = db.Column(db.String(250))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    printed_count = db.Column(db.Integer, default=0)

    payment = db.relationship("Payment", backref=db.backref("receipt", uselist=False))

    def __repr__(self):
        return f"<Receipt for payment {self.payment_id}>"
