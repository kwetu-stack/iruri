import os
import uuid
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.buyers import buyers
from app.buyers.models import Buyer
from app.extensions import db

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
BUYER_TYPES = (
    "Individual",
    "Company",
    "Investor",
    "Diaspora Client",
    "Institution",
    "SACCO",
    "Government",
)
BUYER_FIELDS = (
    "buyer_type",
    "full_name",
    "company_name",
    "national_id",
    "passport_number",
    "kra_pin",
    "phone",
    "alternative_phone",
    "email",
    "county",
    "town",
    "address",
    "postal_address",
    "preferred_property_type",
    "preferred_county",
    "preferred_town",
    "financing_method",
    "notes",
)


def _upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "buyers")
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


def _save_photo(uploaded_file):
    extension = secure_filename(uploaded_file.filename).rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    uploaded_file.save(os.path.join(_upload_folder(), filename))
    return filename


def _remove_photo(filename):
    if filename:
        path = os.path.join(_upload_folder(), filename)
        if os.path.isfile(path):
            os.remove(path)


def _photo_error(uploaded_file):
    if uploaded_file and uploaded_file.filename:
        if not _valid_image(uploaded_file):
            return "Only JPG, JPEG, PNG, and WEBP images are allowed."
        if not _within_size(uploaded_file):
            return "The profile photo must be 10 MB or smaller."
    return None


def _parse_budget(value, label):
    value = value.strip()
    if not value:
        return None, None
    try:
        amount = float(value)
    except ValueError:
        return None, f"{label} must be a valid amount."
    if amount < 0:
        return None, f"{label} cannot be negative."
    return amount, None


def _buyer_values(form):
    values = {field: form.get(field, "").strip() or None for field in BUYER_FIELDS}
    values["budget_min"], error = _parse_budget(
        form.get("budget_min", ""), "Minimum budget"
    )
    if error:
        return values, error
    values["budget_max"], error = _parse_budget(
        form.get("budget_max", ""), "Maximum budget"
    )
    if error:
        return values, error
    if (
        values["budget_min"] is not None
        and values["budget_max"] is not None
        and values["budget_min"] > values["budget_max"]
    ):
        return values, "Minimum budget cannot exceed maximum budget."
    values["verified"] = form.get("verified") == "on"
    values["active"] = form.get("active") == "on"
    return values, None


def _validation_error(form):
    buyer_type = form.get("buyer_type", "").strip()
    if not buyer_type or buyer_type not in BUYER_TYPES:
        return "Select a valid buyer type."
    if not form.get("phone", "").strip():
        return "Phone is required."
    if buyer_type == "Individual" and not form.get("full_name", "").strip():
        return "Full name is required for individuals."
    if buyer_type == "Company" and not form.get("company_name", "").strip():
        return "Company name is required for companies."
    return None


@buyers.route("/")
@login_required
def index():
    buyer_list = Buyer.query.order_by(Buyer.created_at.desc()).all()
    return render_template("buyers/index.html", buyers=buyer_list)


@buyers.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        error = _validation_error(request.form)
        uploaded_file = request.files.get("profile_photo")
        if not error:
            error = _photo_error(uploaded_file)
        values = None
        if not error:
            values, error = _buyer_values(request.form)
        if error:
            flash(error, "danger")
            return render_template("buyers/create.html", buyer_types=BUYER_TYPES)
        if uploaded_file and uploaded_file.filename:
            values["profile_photo"] = _save_photo(uploaded_file)
        buyer = Buyer(buyer_number="TEMP", **values)
        db.session.add(buyer)
        db.session.flush()
        buyer.buyer_number = f"BUY-{datetime.utcnow().year}-{buyer.id:06d}"
        db.session.commit()
        flash("Buyer added successfully.", "success")
        return redirect(url_for("buyers.index"))
    return render_template("buyers/create.html", buyer_types=BUYER_TYPES)


@buyers.route("/<int:id>")
@login_required
def details(id):
    return render_template("buyers/details.html", buyer=Buyer.query.get_or_404(id))


@buyers.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    buyer = Buyer.query.get_or_404(id)
    if request.method == "POST":
        error = _validation_error(request.form)
        uploaded_file = request.files.get("profile_photo")
        if not error:
            error = _photo_error(uploaded_file)
        values = None
        if not error:
            values, error = _buyer_values(request.form)
        if error:
            flash(error, "danger")
            return render_template(
                "buyers/edit.html", buyer=buyer, buyer_types=BUYER_TYPES
            )
        old_photo = buyer.profile_photo
        if uploaded_file and uploaded_file.filename:
            values["profile_photo"] = _save_photo(uploaded_file)
        for field, value in values.items():
            setattr(buyer, field, value)
        db.session.commit()
        if uploaded_file and uploaded_file.filename:
            _remove_photo(old_photo)
        flash("Buyer updated successfully.", "success")
        return redirect(url_for("buyers.details", id=buyer.id))
    return render_template("buyers/edit.html", buyer=buyer, buyer_types=BUYER_TYPES)


@buyers.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):
    buyer = Buyer.query.get_or_404(id)
    if request.method == "POST":
        photo = buyer.profile_photo
        db.session.delete(buyer)
        db.session.commit()
        _remove_photo(photo)
        flash("Buyer deleted successfully.", "success")
        return redirect(url_for("buyers.index"))
    return render_template("buyers/delete.html", buyer=buyer)
