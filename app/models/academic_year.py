from datetime import datetime
from app.extensions import db


class AcademicYear(db.Model):
    """An academic year e.g. 2026/2027. Only one should be active at a time
    per school (enforced at the application layer, not DB, because archiving
    a year shouldn't break historical references)."""

    __tablename__ = "academic_years"
    __table_args__ = (
        db.UniqueConstraint("school_id", "name", name="uq_academic_years_school_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    name = db.Column(db.String(50), nullable=False)          # "2026/2027"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_current = db.Column(db.Boolean, default=False)        # the "live" year
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    terms = db.relationship("Term", backref="academic_year", lazy="dynamic",
                            cascade="all, delete-orphan", order_by="Term.start_date")

    def __repr__(self):
        return f"<AcademicYear {self.name}>"


class Term(db.Model):
    """A term/semester within an academic year e.g. First Term, Second Term."""

    __tablename__ = "terms"
    __table_args__ = (
        db.UniqueConstraint("academic_year_id", "name", name="uq_terms_year_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    name = db.Column(db.String(50), nullable=False)          # "First Term"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_current = db.Column(db.Boolean, default=False)        # the "live" term
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Term {self.name} ({self.academic_year.name if self.academic_year else ''})>"
