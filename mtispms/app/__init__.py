import os
from flask import Flask, render_template, request
from flask_login import current_user
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, mail


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

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

    # ---- Context processors ----
    @app.context_processor
    def inject_globals():
        from app.models import Notification
        unread_count = 0
        if current_user.is_authenticated:
            q = Notification.query.filter(
                (Notification.user_id == current_user.id)
                | ((Notification.user_id.is_(None)) & (Notification.school_id == current_user.school_id))
            ).filter_by(is_read=False)
            unread_count = q.count()
        return {"unread_notifications": unread_count, "app_name": "MT-ISPMS"}

    # ---- Error handlers ----
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
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
