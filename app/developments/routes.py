import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.developments import developments
from app.developments.models import Development
from app.developers.models import Developer
from app.extensions import db
from app.utils.permissions import require_permission

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PROPERTY_TYPES = ("Apartment", "House", "Land", "Commercial", "Mixed Use")
STATUSES = ("Planned", "Under Construction", "Completed", "Sold Out")


def _upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "developments")
    os.makedirs(folder, exist_ok=True)
    return folder


def _save_cover_image(uploaded_file):
    filename = secure_filename(uploaded_file.filename or "")
    extension = filename.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    uploaded_file.save(os.path.join(_upload_folder(), stored_name))
    return stored_name


def _remove_cover_image(filename):
    if filename:
        path = os.path.join(_upload_folder(), filename)
        if os.path.isfile(path):
            os.remove(path)


def _valid_image(uploaded_file):
    filename = secure_filename(uploaded_file.filename or "")
    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _development_values(form):
    values = {
        field: form.get(field, "").strip() or None
        for field in (
            "name",
            "description",
            "county",
            "town",
            "neighbourhood",
            "property_type",
            "status",
        )
    }
    if not values["name"] or not values["county"] or not values["town"]:
        raise ValueError("Development name, county, and town are required.")
    if values["property_type"] not in PROPERTY_TYPES:
        raise ValueError("Select a valid property type.")
    if values["status"] not in STATUSES:
        raise ValueError("Select a valid development status.")

    completion_date = form.get("completion_date", "").strip()
    try:
        values["completion_date"] = (
            datetime.strptime(completion_date, "%Y-%m-%d").date()
            if completion_date
            else None
        )
    except ValueError as error:
        raise ValueError("Completion date must be a valid date.") from error

    starting_price = form.get("starting_price", "").strip()
    try:
        values["starting_price"] = Decimal(starting_price) if starting_price else None
    except InvalidOperation as error:
        raise ValueError("Starting price must be a valid amount.") from error
    if values["starting_price"] is not None and values["starting_price"] < 0:
        raise ValueError("Starting price cannot be negative.")
    return values


def _form_context():
    return {
        "developers": Developer.query.order_by(Developer.company_name).all(),
        "property_types": PROPERTY_TYPES,
        "statuses": STATUSES,
    }


@developments.get("/")
def index():
    development_list = Development.query.order_by(Development.created_at.desc()).all()
    return render_template("public/developments.html", developments=development_list)


@developments.get("/<int:id>")
def public_detail(id):
    development = Development.query.get_or_404(id)
    return render_template("public/development_detail.html", development=development)


@developments.get("/admin")
@require_permission("development.view")
def admin_index():
    development_list = Development.query.order_by(Development.created_at.desc()).all()
    return render_template("developments/index.html", developments=development_list)


@developments.route("/admin/create", methods=["GET", "POST"])
@require_permission("development.create")
def create():
    context = _form_context()
    if request.method == "POST":
        try:
            values = _development_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("developments/create.html", **context)
        developer = Developer.query.get(request.form.get("developer_id", type=int))
        if not developer:
            flash("Select a valid developer.", "danger")
            return render_template("developments/create.html", **context)
        uploaded_file = request.files.get("cover_image")
        if uploaded_file and uploaded_file.filename:
            if not _valid_image(uploaded_file):
                flash("Only JPG, JPEG, PNG, and WEBP images are allowed.", "danger")
                return render_template("developments/create.html", **context)
            values["cover_image"] = _save_cover_image(uploaded_file)
        values["developer_id"] = developer.id
        development = Development(**values)
        db.session.add(development)
        db.session.commit()
        flash("Development added successfully.", "success")
        return redirect(url_for("developments.admin_index"))
    return render_template("developments/create.html", **context)


@developments.route("/admin/<int:id>/edit", methods=["GET", "POST"])
@require_permission("development.edit")
def edit(id):
    development = Development.query.get_or_404(id)
    context = _form_context()
    if request.method == "POST":
        try:
            values = _development_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template(
                "developments/edit.html", development=development, **context
            )
        developer = Developer.query.get(request.form.get("developer_id", type=int))
        if not developer:
            flash("Select a valid developer.", "danger")
            return render_template(
                "developments/edit.html", development=development, **context
            )
        uploaded_file = request.files.get("cover_image")
        if uploaded_file and uploaded_file.filename:
            if not _valid_image(uploaded_file):
                flash("Only JPG, JPEG, PNG, and WEBP images are allowed.", "danger")
                return render_template(
                    "developments/edit.html", development=development, **context
                )
            old_cover_image = development.cover_image
            values["cover_image"] = _save_cover_image(uploaded_file)
        else:
            old_cover_image = None
        values["developer_id"] = developer.id
        for field, value in values.items():
            setattr(development, field, value)
        db.session.commit()
        if old_cover_image:
            _remove_cover_image(old_cover_image)
        flash("Development updated successfully.", "success")
        return redirect(url_for("developments.admin_detail", id=development.id))
    return render_template("developments/edit.html", development=development, **context)


@developments.get("/admin/<int:id>")
@require_permission("development.view")
def admin_detail(id):
    development = Development.query.get_or_404(id)
    return render_template("developments/details.html", development=development)


@developments.route("/admin/<int:id>/delete", methods=["GET", "POST"])
@require_permission("development.delete")
def delete(id):
    development = Development.query.get_or_404(id)
    if request.method == "POST":
        cover_image = development.cover_image
        db.session.delete(development)
        db.session.commit()
        _remove_cover_image(cover_image)
        flash("Development deleted successfully.", "success")
        return redirect(url_for("developments.admin_index"))
    return render_template("developments/delete.html", development=development)
