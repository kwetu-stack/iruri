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


@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            login_user(user)

            flash("Welcome back!", "success")

            return redirect(url_for("dashboard.index"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "info")

    return redirect(url_for("auth.login"))


@auth.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html", user=current_user)
