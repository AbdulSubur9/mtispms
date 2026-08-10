from datetime import datetime, date
from app.extensions import db


class AttendanceStatus:
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"

    ALL = [PRESENT, ABSENT, LATE, EXCUSED]
    LABELS = {PRESENT: "Present", ABSENT: "Absent", LATE: "Late", EXCUSED: "Excused"}


class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (
        # One attendance record per student, per class, per day.
        db.UniqueConstraint("class_id", "student_id", "attendance_date", name="uq_attendance_class_student_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    attendance_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default=AttendanceStatus.PRESENT)
    remarks = db.Column(db.String(250))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    classroom = db.relationship("ClassRoom", foreign_keys=[class_id])
    teacher = db.relationship("User", foreign_keys=[teacher_id])

    @property
    def status_label(self):
        return AttendanceStatus.LABELS.get(self.status, self.status)

    def __repr__(self):
        return f"<Attendance {self.student_id} {self.attendance_date} {self.status}>"
