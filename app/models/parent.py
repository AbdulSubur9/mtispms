from datetime import datetime
from app.extensions import db


class Parent(db.Model):
    """A parent/guardian linked to a User account so they can log in to the
    Parent Portal and view their children's results, attendance, and payments."""

    __tablename__ = "parents"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Link to the primary student this parent is responsible for.
    # A parent can have multiple children via the parent_students join table.
    primary_student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)

    relationship = db.Column(db.String(30), default="Guardian")   # Father, Mother, Uncle, etc.
    occupation = db.Column(db.String(100))
    address = db.Column(db.String(250))
    emergency_contact = db.Column(db.String(30))
    emergency_contact_name = db.Column(db.String(120))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])
    primary_student = db.relationship("Student", foreign_keys=[primary_student_id])
    # Explicit reverse side of ParentStudent.parent below (was previously
    # created implicitly via backref="parent_links" on ParentStudent.parent;
    # now declared explicitly here so both sides of this association-object
    # relationship consistently use back_populates rather than mixing
    # backref and back_populates on the same model).
    parent_links = db.relationship("ParentStudent", back_populates="parent")

    @property
    def full_name(self):
        return self.user.full_name if self.user else ""

    @property
    def email(self):
        return self.user.email if self.user else ""

    @property
    def phone(self):
        return self.user.phone if self.user else ""

    def __repr__(self):
        return f"<Parent {self.full_name}>"


class ParentStudent(db.Model):
    """Join table: a parent can have many students, a student can have many parents."""

    __tablename__ = "parent_students"
    __table_args__ = (
        db.UniqueConstraint("parent_id", "student_id", name="uq_parent_students_parent_student"),
    )

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    relationship = db.Column(db.String(30), default="Guardian")
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship("Parent", back_populates="parent_links")
    student = db.relationship("Student", back_populates="parent_links")
