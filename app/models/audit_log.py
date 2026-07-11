from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    action = db.Column(db.String(50), nullable=False)  # login, logout, payment_created, ...
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    description = db.Column(db.String(300))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])

    @staticmethod
    def log(action, description=None, entity_type=None, entity_id=None, user=None, school_id=None, ip_address=None):
        entry = AuditLog(
            action=action,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=getattr(user, "id", None),
            school_id=school_id if school_id is not None else getattr(user, "school_id", None),
            ip_address=ip_address,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    def __repr__(self):
        return f"<AuditLog {self.action} by user {self.user_id}>"
