from datetime import datetime, date
from app.extensions import db


class ApplicationStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    ALL = [PENDING, APPROVED, REJECTED]
    LABELS = {PENDING: "Pending Review", APPROVED: "Approved", REJECTED: "Rejected"}


class StudentApplication(db.Model):
    """Student admission/application form. Kept separate from Student so an
    application can be filled, printed, and reviewed before a student record
    is actually created (e.g. before admission is confirmed)."""
    __tablename__ = "student_applications"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)  # linked once approved & admitted

    # Student details
    full_name = db.Column(db.String(160), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    previous_school = db.Column(db.String(150))
    address = db.Column(db.String(250))

    # Parent / Guardian details
    guardian_name = db.Column(db.String(150), nullable=False)
    guardian_phone = db.Column(db.String(30), nullable=False)
    guardian_occupation = db.Column(db.String(120))
    guardian_address = db.Column(db.String(250))

    # Emergency contact
    emergency_contact_name = db.Column(db.String(150))
    emergency_contact_phone = db.Column(db.String(30))
    emergency_contact_relationship = db.Column(db.String(80))

    # Health information (matches the reference admission form's Y/N +
    # details structure)
    has_medical_condition = db.Column(db.Boolean, default=False)
    medical_condition_details = db.Column(db.String(500))

    # Declaration
    declaration_accepted = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default=ApplicationStatus.PENDING)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    application_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])
    school = db.relationship("School", foreign_keys=[school_id])

    @property
    def status_label(self):
        return ApplicationStatus.LABELS.get(self.status, self.status)

    def __repr__(self):
        return f"<StudentApplication {self.full_name} ({self.status})>"
