from datetime import datetime
from app.extensions import db


class Subject(db.Model):
    """Subjects are never hard-coded - each school creates its own
    (Qur'an, Arabic, Hadith, ...) via the Subjects settings page."""
    __tablename__ = "subjects"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_subjects_school_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Subject {self.name}>"


class GradingScaleBand(db.Model):
    __tablename__ = "grading_scale_bands"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    grade = db.Column(db.String(5), nullable=False)  # "A", "B", "C", ...
    min_percentage = db.Column(db.Numeric(5, 2), nullable=False)
    max_percentage = db.Column(db.Numeric(5, 2), nullable=False)
    remark = db.Column(db.String(100))  # e.g. "Excellent", "Good"

    def __repr__(self):
        return f"<GradingScaleBand {self.grade} {self.min_percentage}-{self.max_percentage}>"

    @staticmethod
    def default_scale_for(school_id):
        """The sensible default grading scale from the spec (A 80-100 ...
        F below 50), used to seed a new school so grading always works out
        of the box while remaining fully editable."""
        return [
            GradingScaleBand(school_id=school_id, grade="A", min_percentage=80, max_percentage=100, remark="Excellent"),
            GradingScaleBand(school_id=school_id, grade="B", min_percentage=70, max_percentage=79.99, remark="Very Good"),
            GradingScaleBand(school_id=school_id, grade="C", min_percentage=60, max_percentage=69.99, remark="Good"),
            GradingScaleBand(school_id=school_id, grade="D", min_percentage=50, max_percentage=59.99, remark="Pass"),
            GradingScaleBand(school_id=school_id, grade="F", min_percentage=0, max_percentage=49.99, remark="Fail"),
        ]

    @staticmethod
    def grade_for_percentage(school_id, percentage):
        band = (
            GradingScaleBand.query.filter(
                GradingScaleBand.school_id == school_id,
                GradingScaleBand.min_percentage <= percentage,
                GradingScaleBand.max_percentage >= percentage,
            )
            .order_by(GradingScaleBand.min_percentage.desc())
            .first()
        )
        return (band.grade, band.remark) if band else ("-", "")


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)  # e.g. "First Term Examination 2026"
    exam_type = db.Column(db.String(50), default="Examination")  # Exam, Test, Quiz, etc.
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="draft")  # draft, published, locked
    is_published = db.Column(db.Boolean, default=False)  # deprecated: use status instead
    published_at = db.Column(db.DateTime)
    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    locked_at = db.Column(db.DateTime)
    locked_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    classroom = db.relationship("ClassRoom", foreign_keys=[class_id])
    academic_year = db.relationship("AcademicYear", foreign_keys=[academic_year_id])
    term = db.relationship("Term", foreign_keys=[term_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    published_by = db.relationship("User", foreign_keys=[published_by_id])
    locked_by = db.relationship("User", foreign_keys=[locked_by_id])
    exam_subjects = db.relationship("ExamSubject", backref="exam", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exam {self.name}>"


class ExamSubject(db.Model):
    """Join of an Exam to one of its Subjects, carrying the max marks for
    that subject in that exam (max marks can differ exam to exam)."""
    __tablename__ = "exam_subjects"
    __table_args__ = (
        db.UniqueConstraint("exam_id", "subject_id", name="uq_exam_subjects_exam_subject"),
    )

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    max_marks = db.Column(db.Numeric(6, 2), nullable=False, default=100)

    subject = db.relationship("Subject", foreign_keys=[subject_id])
    results = db.relationship("Result", backref="exam_subject", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExamSubject exam={self.exam_id} subject={self.subject_id}>"


class Result(db.Model):
    """One student's score for one subject within one exam."""
    __tablename__ = "results"
    __table_args__ = (
        db.UniqueConstraint("exam_subject_id", "student_id", name="uq_results_examsubject_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    exam_subject_id = db.Column(db.Integer, db.ForeignKey("exam_subjects.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    marks_obtained = db.Column(db.Numeric(6, 2), nullable=False)
    teacher_comment = db.Column(db.String(250))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Result student={self.student_id} marks={self.marks_obtained}>"
