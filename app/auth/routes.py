from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_login import current_user, login_user, logout_user, login_required

from app.auth import auth
from app.auth.models import User
from app.audit.service import record_audit


@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            login_user(user)
            record_audit(
                "Login",
                "Authentication",
                "User logged in successfully",
                "User",
                user.id,
            )

            flash("Welcome back!", "success")

            return redirect(url_for("dashboard.index"))

        record_audit(
            "Failed Login",
            "Authentication",
            "Failed login attempt",
            "User",
            user.id if user else None,
            status="Failed",
        )
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth.route("/logout")
@login_required
def logout():
    record_audit("Logout", "Authentication", "User logged out", "User", current_user.id)
    logout_user()

    flash("You have been logged out.", "info")

    return redirect(url_for("auth.login"))


@auth.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html", user=current_user)
