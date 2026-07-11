from datetime import datetime, date
from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)

    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)  # STU-0001
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    guardian_name = db.Column(db.String(120))
    guardian_contact = db.Column(db.String(30))
    admission_date = db.Column(db.Date, default=date.today)
    photo = db.Column(db.String(250))
    status = db.Column(db.String(20), default="active")  # active / inactive / deactivated

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payments = db.relationship("Payment", backref="student", lazy="dynamic")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def total_paid(self):
        from app.models.payment import Payment
        total = (
            db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
            .filter(Payment.student_id == self.id, Payment.is_void.is_(False))
            .scalar()
        )
        return float(total or 0)

    @staticmethod
    def generate_student_id(school_id):
        last = (
            Student.query.filter_by(school_id=school_id)
            .order_by(Student.id.desc())
            .first()
        )
        next_num = 1
        if last and last.student_id and "-" in last.student_id:
            try:
                next_num = int(last.student_id.split("-")[-1]) + 1
            except ValueError:
                next_num = Student.query.filter_by(school_id=school_id).count() + 1
        return f"STU-{next_num:04d}"

    def __repr__(self):
        return f"<Student {self.student_id} {self.full_name}>"
