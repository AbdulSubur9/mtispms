from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Role:
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    ACCOUNTANT = "accountant"
    COLLECTOR = "collector"
    TEACHER = "teacher"
    PARENT = "parent"

    ALL = [SUPER_ADMIN, SCHOOL_ADMIN, ACCOUNTANT, COLLECTOR, TEACHER, PARENT]

    LABELS = {
        SUPER_ADMIN: "Super Admin",
        SCHOOL_ADMIN: "School Admin",
        ACCOUNTANT: "Accountant",
        COLLECTOR: "Collector",
        TEACHER: "Teacher",
        PARENT: "Parent",
    }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)

    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30))
    photo = db.Column(db.String(250))

    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=Role.COLLECTOR)

    is_active_user = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments_collected = db.relationship(
        "Payment", backref="collector", lazy="dynamic", foreign_keys="Payment.collector_id"
    )
    expenses_recorded = db.relationship(
        "Expense", backref="recorded_by_user", lazy="dynamic", foreign_keys="Expense.recorded_by_id"
    )

    # Flask-Login required property override (avoid clashing with is_active_user)
    @property
    def is_active(self):
        return self.is_active_user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def role_label(self):
        from app.models.user import Role
        return Role.LABELS.get(self.role, self.role)

    def has_role(self, *roles):
        return self.role in roles

    def can_manage_school(self, school_id):
        if self.role == Role.SUPER_ADMIN:
            return True
        return self.school_id == school_id

    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({"user_id": self.id}, salt="password-reset")

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, salt="password-reset", max_age=max_age)
        except Exception:
            return None
        return User.query.get(data.get("user_id"))

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
