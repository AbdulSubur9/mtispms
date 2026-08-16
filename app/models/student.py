from datetime import datetime, date
from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"
    __table_args__ = (
        # Student IDs are human-readable and scoped PER SCHOOL (e.g. every school
        # can independently have a "STU-0001"). The uniqueness constraint must
        # therefore be composite, not a bare global unique column - otherwise the
        # second school to register its first student collides with the first
        # school's STU-0001 and the insert fails with an IntegrityError.
        db.UniqueConstraint("school_id", "student_id", name="uq_students_school_student_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=True)

    student_id = db.Column(db.String(20), nullable=False, index=True)  # STU-0001 (unique within school)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    guardian_name = db.Column(db.String(120))
    guardian_contact = db.Column(db.String(30))
    guardian_email = db.Column(db.String(120))
    admission_date = db.Column(db.Date, default=date.today)
    photo = db.Column(db.String(250))
    status = db.Column(db.String(20), default="active")  # active / inactive / deactivated / graduated
    promotion_status = db.Column(db.String(20), default="pending")  # pending, promoted, repeated, graduated

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    classroom = db.relationship("ClassRoom", back_populates="students", foreign_keys=[class_id])
    academic_year = db.relationship("AcademicYear", foreign_keys=[academic_year_id])
    payments = db.relationship("Payment", backref="student", lazy="dynamic")
    applications = db.relationship("StudentApplication", backref="student", lazy="dynamic")
    attendance_records = db.relationship("Attendance", backref="student", lazy="dynamic")
    parent_links = db.relationship("ParentStudent", back_populates="student", lazy="dynamic")
    results = db.relationship("Result", backref="student", lazy="dynamic")

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
        """Generate the next STU-XXXX id, unique *within this school only*.
        Scans all existing IDs for the school (not just the last row) so that
        deletions or out-of-order inserts never cause a collision."""
        existing = (
            db.session.query(Student.student_id)
            .filter(Student.school_id == school_id, Student.student_id.like("STU-%"))
            .all()
        )
        max_num = 0
        for (sid,) in existing:
            try:
                num = int(sid.split("-")[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"STU-{max_num + 1:04d}"

    def __repr__(self):
        return f"<Student {self.student_id} {self.full_name}>"
