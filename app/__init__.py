import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, url_for, redirect
from flask_login import current_user
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, mail


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    _configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---- Blueprints ----
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.students.routes import students_bp
    from app.classes.routes import classes_bp
    from app.payments.routes import payments_bp
    from app.expenses.routes import expenses_bp
    from app.reports.routes import reports_bp
    from app.admin.routes import admin_bp
    from app.api.routes import api_bp
    from app.search.routes import search_bp
    from app.attendance.routes import attendance_bp
    from app.applications.routes import applications_bp
    from app.notifications.routes import notifications_bp
    from app.exams.routes import exams_bp
    from app.academics.routes import academics_bp
    from app.fee_structures.routes import fee_structures_bp
    from app.parents.routes import parents_bp
    from app.files.routes import files_bp
    from app.parent_management.routes import parent_management_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(students_bp, url_prefix="/students")
    app.register_blueprint(classes_bp, url_prefix="/classes")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp)
    app.register_blueprint(search_bp, url_prefix="/search")
    app.register_blueprint(attendance_bp, url_prefix="/attendance")
    app.register_blueprint(applications_bp, url_prefix="/applications")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(exams_bp, url_prefix="/exams")
    app.register_blueprint(academics_bp, url_prefix="/academics")
    app.register_blueprint(fee_structures_bp, url_prefix="/fee-structures")
    app.register_blueprint(parents_bp, url_prefix="/parents")
    app.register_blueprint(files_bp)
    app.register_blueprint(parent_management_bp, url_prefix="/parent-management")

    # ---- Forced password change enforcement ----
    @app.before_request
    def _enforce_password_change():
        """A newly-created Parent (or any user) with must_change_password
        set can't just navigate away from the change-password page to skip
        it - every request gets redirected there until they actually
        change it. Exempts the change-password page itself, logout, and
        static assets so the flow doesn't lock the user out."""
        if not current_user.is_authenticated or not current_user.must_change_password:
            return None
        allowed_endpoints = {"auth.change_password", "auth.logout", "static", "files.serve_file"}
        if request.endpoint in allowed_endpoints:
            return None
        return redirect(url_for("auth.change_password", next=request.path))

    # ---- Context processors ----
    @app.context_processor
    def inject_globals():
        from app.models import Notification, School
        from app.utils.helpers import current_school_id, is_super_admin

        unread_count = 0
        all_schools = []
        active_school_id = None
        if current_user.is_authenticated:
            q = Notification.query.filter(
                (Notification.user_id == current_user.id)
                | ((Notification.user_id.is_(None)) & (Notification.school_id == current_user.school_id))
            ).filter_by(is_read=False)
            unread_count = q.count()

            if is_super_admin():
                all_schools = School.query.order_by(School.name).all()
                active_school_id = current_school_id()

        return {
            "unread_notifications": unread_count,
            "app_name": "MT-ISPMS",
            "all_schools": all_schools,
            "active_school_id": active_school_id,
        }

    # ---- Error handlers ----
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(e):
        from flask import flash, redirect, request
        max_mb = app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024) // (1024 * 1024)
        flash(f"That upload is too large. Maximum file size is {max_mb}MB.", "danger")
        return redirect(request.referrer or url_for("dashboard.index")), 302

    @app.errorhandler(500)
    def server_error(e):
        # Log the *real* exception server-side (with traceback) before ever
        # showing the user a generic error page - previously nothing here
        # was logged at all, so a 500 gave zero information for debugging.
        app.logger.error("Unhandled exception on %s %s", request.method, request.path, exc_info=e)
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # ---- CLI commands ----
    @app.cli.command("seed")
    def seed_command():
        """Seed the database with demo data: flask seed"""
        from seed import run_seed
        run_seed()
        print("Database seeded successfully.")

    return app


def _configure_logging(app):
    """Route application errors to a rotating log file (in addition to the
    console) so production issues are diagnosable after the fact instead of
    only being visible as a blank "Internal Server Error" to the user."""
    if app.testing:
        return

    log_dir = os.path.join(app.instance_path, "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "mtispms.log"), maxBytes=1_000_000, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(pathname)s:%(lineno)d]: %(message)s"
    ))
    file_handler.setLevel(logging.INFO if app.debug else logging.WARNING)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO if app.debug else logging.WARNING)
