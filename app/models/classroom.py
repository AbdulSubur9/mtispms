from datetime import datetime
from app.extensions import db


class ClassRoom(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(250))
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    students = db.relationship("Student", back_populates="classroom", lazy="dynamic")

    @property
    def student_count(self):
        return self.students.filter_by(status="active").count()

    def __repr__(self):
        return f"<ClassRoom {self.name}>"
