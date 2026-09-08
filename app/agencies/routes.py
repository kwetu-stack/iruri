import os
import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.agencies import agencies
from app.agencies.models import Agency
from app.extensions import db

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "agencies")
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


def _agency_values(form):
    values = {
        field: form.get(field, "").strip() or None
        for field in (
            "agency_name",
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
        )
    }
    try:
        values["year_established"] = (
            int(form.get("year_established", ""))
            if form.get("year_established", "").strip()
            else None
        )
    except ValueError:
        raise ValueError("Year established must be a whole number.")
    values["is_active"] = form.get("is_active") == "on"
    return values


def _logo_error(uploaded_file):
    if uploaded_file and uploaded_file.filename:
        if not _valid_image(uploaded_file):
            return "Only JPG, JPEG, PNG, and WEBP images are allowed."
        if not _within_size(uploaded_file):
            return "The agency logo must be 10 MB or smaller."
    return None


@agencies.route("/")
@login_required
def index():
    agency_list = Agency.query.order_by(Agency.created_at.desc()).all()
    return render_template("agencies/index.html", agencies=agency_list)


@agencies.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        if (
            not request.form.get("agency_name", "").strip()
            or not request.form.get("phone", "").strip()
        ):
            flash("Agency name and phone are required.", "danger")
            return render_template("agencies/create.html")
        try:
            values = _agency_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("agencies/create.html")
        uploaded_file = request.files.get("logo")
        error = _logo_error(uploaded_file)
        if error:
            flash(error, "danger")
            return render_template("agencies/create.html")
        if uploaded_file and uploaded_file.filename:
            values["logo"] = _save_logo(uploaded_file)
        agency = Agency(agency_number="TEMP", **values)
        db.session.add(agency)
        db.session.flush()
        agency.agency_number = f"AGY-2026-{agency.id:06d}"
        db.session.commit()
        flash("Agency added successfully.", "success")
        return redirect(url_for("agencies.index"))
    return render_template("agencies/create.html")


@agencies.route("/<int:id>")
@login_required
def details(id):
    return render_template("agencies/details.html", agency=Agency.query.get_or_404(id))


@agencies.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    agency = Agency.query.get_or_404(id)
    if request.method == "POST":
        if (
            not request.form.get("agency_name", "").strip()
            or not request.form.get("phone", "").strip()
        ):
            flash("Agency name and phone are required.", "danger")
            return render_template("agencies/edit.html", agency=agency)
        try:
            values = _agency_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("agencies/edit.html", agency=agency)
        uploaded_file = request.files.get("logo")
        error = _logo_error(uploaded_file)
        if error:
            flash(error, "danger")
            return render_template("agencies/edit.html", agency=agency)
        old_logo = agency.logo
        if uploaded_file and uploaded_file.filename:
            values["logo"] = _save_logo(uploaded_file)
        for field, value in values.items():
            setattr(agency, field, value)
        db.session.commit()
        if uploaded_file and uploaded_file.filename:
            _remove_logo(old_logo)
        flash("Agency updated successfully.", "success")
        return redirect(url_for("agencies.details", id=agency.id))
    return render_template("agencies/edit.html", agency=agency)


@agencies.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):
    agency = Agency.query.get_or_404(id)
    if request.method == "POST":
        logo = agency.logo
        db.session.delete(agency)
        db.session.commit()
        _remove_logo(logo)
        flash("Agency deleted successfully.", "success")
        return redirect(url_for("agencies.index"))
    return render_template("agencies/delete.html", agency=agency)
