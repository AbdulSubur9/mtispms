from datetime import datetime, date
from app.extensions import db


class FeeStructure(db.Model):
    """Defines the expected fee amount for a given class, academic year,
    term, and payment type. This is what drives the 'Students Owing' report
    and the outstanding balance calculations."""

    __tablename__ = "fee_structures"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "class_id", "academic_year_id", "term_id", "payment_type_id",
            name="uq_fee_structures_school_class_year_term_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("terms.id"), nullable=False)
    payment_type_id = db.Column(db.Integer, db.ForeignKey("school_payment_types.id"), nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    is_mandatory = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(250))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    classroom = db.relationship("ClassRoom", foreign_keys=[class_id])
    academic_year = db.relationship("AcademicYear", foreign_keys=[academic_year_id])
    term = db.relationship("Term", foreign_keys=[term_id])
    payment_type = db.relationship("SchoolPaymentType", foreign_keys=[payment_type_id])

    def __repr__(self):
        return f"<FeeStructure {self.classroom.name if self.classroom else ''} {self.amount}>"

    @property
    def display_name(self):
        parts = []
        if self.classroom:
            parts.append(self.classroom.name)
        if self.payment_type:
            parts.append(self.payment_type.name)
        if self.term:
            parts.append(self.term.name)
        return " — ".join(parts) if parts else f"Fee #{self.id}"
