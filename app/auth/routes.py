from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app.extensions import db, mail
from app.models import User, AuditLog
from app.auth.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username.data.strip()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active_user:
                flash("Your account has been deactivated. Contact your administrator.", "danger")
                return redirect(url_for("auth.login"))

            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            AuditLog.log(
                "login", description=f"{user.username} logged in", user=user,
                ip_address=request.remote_addr,
            )
            flash(f"Welcome back, {user.first_name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    AuditLog.log(
        "logout", description=f"{current_user.username} logged out", user=current_user,
        ip_address=request.remote_addr,
    )
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            try:
                msg = Message(
                    "MT-ISPMS Password Reset",
                    sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                    recipients=[user.email],
                )
                msg.body = (
                    f"Hello {user.first_name},\n\n"
                    f"Click the link below to reset your password. This link expires in 30 minutes.\n\n"
                    f"{reset_url}\n\nIf you didn't request this, ignore this email."
                )
                mail.send(msg)
            except Exception:
                current_app.logger.exception("Failed to send password reset email")
        flash("If that email exists in our system, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    user = User.verify_reset_token(token)
    if not user:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been updated. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("auth/change_password.html", form=form)
