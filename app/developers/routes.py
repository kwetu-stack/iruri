import os
import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.developers import developers
from app.developers.models import Developer
from app.extensions import db

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "developers")
    os.makedirs(folder, exist_ok=True)
    return folder


def _valid_image(uploaded_file):
    filename = secure_filename(uploaded_file.filename or "")
    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _within_size(uploaded_file):
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    return size <= MAX_IMAGE_SIZE


def _save_logo(uploaded_file):
    extension = secure_filename(uploaded_file.filename).rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    uploaded_file.save(os.path.join(_upload_folder(), filename))
    return filename


def _remove_logo(filename):
    if filename:
        path = os.path.join(_upload_folder(), filename)
        if os.path.isfile(path):
            os.remove(path)


def _developer_values(form):
    values = {
        field: form.get(field, "").strip() or None
        for field in (
            "company_name",
            "registration_number",
            "license_number",
            "kra_pin",
            "phone",
            "alternative_phone",
            "email",
            "website",
            "county",
            "town",
            "address",
            "postal_address",
            "description",
            "specialization",
        )
    }
    try:
        values["year_established"] = (
            int(form.get("year_established", ""))
            if form.get("year_established", "").strip()
            else None
        )
        values["total_projects"] = (
            int(form.get("total_projects", "0").strip())
            if form.get("total_projects", "").strip()
            else 0
        )
    except ValueError:
        raise ValueError("Year established and total projects must be whole numbers.")
    if values["total_projects"] < 0:
        raise ValueError("Total projects cannot be negative.")
    values["is_verified"] = form.get("is_verified") == "on"
    values["is_active"] = form.get("is_active") == "on"
    return values


def _logo_error(uploaded_file):
    if uploaded_file and uploaded_file.filename:
        if not _valid_image(uploaded_file):
            return "Only JPG, JPEG, PNG, and WEBP images are allowed."
        if not _within_size(uploaded_file):
            return "The developer logo must be 10 MB or smaller."
    return None


@developers.route("/")
@login_required
def index():
    developer_list = Developer.query.order_by(Developer.created_at.desc()).all()
    return render_template("developers/index.html", developers=developer_list)


@developers.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        if (
            not request.form.get("company_name", "").strip()
            or not request.form.get("phone", "").strip()
        ):
            flash("Company name and phone are required.", "danger")
            return render_template("developers/create.html")
        try:
            values = _developer_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("developers/create.html")
        uploaded_file = request.files.get("logo")
        error = _logo_error(uploaded_file)
        if error:
            flash(error, "danger")
            return render_template("developers/create.html")
        if uploaded_file and uploaded_file.filename:
            values["logo"] = _save_logo(uploaded_file)
        developer = Developer(developer_number="TEMP", **values)
        db.session.add(developer)
        db.session.flush()
        developer.developer_number = f"DEV-2026-{developer.id:06d}"
        db.session.commit()
        flash("Developer added successfully.", "success")
        return redirect(url_for("developers.index"))
    return render_template("developers/create.html")


@developers.route("/<int:id>")
@login_required
def details(id):
    return render_template(
        "developers/details.html", developer=Developer.query.get_or_404(id)
    )


@developers.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    developer = Developer.query.get_or_404(id)
    if request.method == "POST":
        if (
            not request.form.get("company_name", "").strip()
            or not request.form.get("phone", "").strip()
        ):
            flash("Company name and phone are required.", "danger")
            return render_template("developers/edit.html", developer=developer)
        try:
            values = _developer_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("developers/edit.html", developer=developer)
        uploaded_file = request.files.get("logo")
        error = _logo_error(uploaded_file)
        if error:
            flash(error, "danger")
            return render_template("developers/edit.html", developer=developer)
        old_logo = developer.logo
        if uploaded_file and uploaded_file.filename:
            values["logo"] = _save_logo(uploaded_file)
        for field, value in values.items():
            setattr(developer, field, value)
        db.session.commit()
        if uploaded_file and uploaded_file.filename:
            _remove_logo(old_logo)
        flash("Developer updated successfully.", "success")
        return redirect(url_for("developers.details", id=developer.id))
    return render_template("developers/edit.html", developer=developer)


@developers.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):
    developer = Developer.query.get_or_404(id)
    if request.method == "POST":
        logo = developer.logo
        db.session.delete(developer)
        db.session.commit()
        _remove_logo(logo)
        flash("Developer deleted successfully.", "success")
        return redirect(url_for("developers.index"))
    return render_template("developers/delete.html", developer=developer)
