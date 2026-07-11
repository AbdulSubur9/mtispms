from datetime import datetime
from app.extensions import db


class School(db.Model):
    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(250))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    logo = db.Column(db.String(250))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="school", lazy="dynamic")
    students = db.relationship("Student", backref="school", lazy="dynamic")
    classes = db.relationship("ClassRoom", backref="school", lazy="dynamic")
    payments = db.relationship("Payment", backref="school", lazy="dynamic")
    expenses = db.relationship("Expense", backref="school", lazy="dynamic")

    def __repr__(self):
        return f"<School {self.name}>"

    @property
    def total_income(self):
        from app.models.payment import Payment
        total = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(
            Payment.school_id == self.id, Payment.is_void.is_(False)
        ).scalar()
        return float(total or 0)

    @property
    def total_expenses(self):
        from app.models.expense import Expense
        total = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).filter(
            Expense.school_id == self.id
        ).scalar()
        return float(total or 0)

    @property
    def current_balance(self):
        return self.total_income - self.total_expenses
