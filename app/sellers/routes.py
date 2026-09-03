import os
import uuid
from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.sellers import sellers
from app.sellers.models import Seller
from app.audit.service import record_audit

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
SELLER_TYPES = (
    "Individual",
    "Company",
    "Institution",
    "Bank",
    "SACCO",
    "Estate administrator",
    "Government agency",
)


def _upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "sellers")
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


def _seller_values(form):
    values = {
        field: form.get(field, "").strip() or None
        for field in (
            "seller_type",
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
            "description",
        )
    }
    values["verified"] = form.get("verified") == "on"
    values["active"] = form.get("active") == "on"
    return values


def _validation_error(form):
    seller_type = form.get("seller_type", "").strip()
    phone = form.get("phone", "").strip()
    full_name = form.get("full_name", "").strip()
    company_name = form.get("company_name", "").strip()
    if not seller_type or seller_type not in SELLER_TYPES:
        return "Select a valid seller type."
    if not phone:
        return "Phone is required."
    if seller_type == "Individual" and not full_name:
        return "Full name is required for individuals."
    if seller_type == "Company" and not company_name:
        return "Company name is required for companies."
    return None


@sellers.route("/")
@login_required
def index():
    seller_list = Seller.query.order_by(Seller.created_at.desc()).all()
    return render_template("sellers/index.html", sellers=seller_list)


@sellers.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        error = _validation_error(request.form)
        if error:
            flash(error, "danger")
            return render_template("sellers/create.html", seller_types=SELLER_TYPES)
        uploaded_file = request.files.get("profile_photo")
        error = _photo_error(uploaded_file)
        if error:
            flash(error, "danger")
            return render_template("sellers/create.html", seller_types=SELLER_TYPES)
        values = _seller_values(request.form)
        if uploaded_file and uploaded_file.filename:
            values["profile_photo"] = _save_photo(uploaded_file)
        seller = Seller(seller_number="TEMP", **values)
        db.session.add(seller)
        db.session.flush()
        seller.seller_number = f"SEL-{datetime.utcnow().year}-{seller.id:06d}"
        db.session.commit()
        record_audit(
            "Create",
            "Marketplace",
            f"Seller {seller.seller_number} created",
            "Seller",
            seller.id,
        )
        flash("Seller added successfully.", "success")
        return redirect(url_for("sellers.index"))
    return render_template("sellers/create.html", seller_types=SELLER_TYPES)


@sellers.route("/<int:id>")
@login_required
def details(id):
    return render_template("sellers/details.html", seller=Seller.query.get_or_404(id))


@sellers.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    seller = Seller.query.get_or_404(id)
    if request.method == "POST":
        error = _validation_error(request.form)
        if error:
            flash(error, "danger")
            return render_template(
                "sellers/edit.html", seller=seller, seller_types=SELLER_TYPES
            )
        uploaded_file = request.files.get("profile_photo")
        error = _photo_error(uploaded_file)
        if error:
            flash(error, "danger")
            return render_template(
                "sellers/edit.html", seller=seller, seller_types=SELLER_TYPES
            )
        old_photo = seller.profile_photo
        values = _seller_values(request.form)
        if uploaded_file and uploaded_file.filename:
            values["profile_photo"] = _save_photo(uploaded_file)
        for field, value in values.items():
            setattr(seller, field, value)
        db.session.commit()
        record_audit(
            "Update",
            "Marketplace",
            f"Seller {seller.seller_number} updated",
            "Seller",
            seller.id,
        )
        if uploaded_file and uploaded_file.filename:
            _remove_photo(old_photo)
        flash("Seller updated successfully.", "success")
        return redirect(url_for("sellers.details", id=seller.id))
    return render_template(
        "sellers/edit.html", seller=seller, seller_types=SELLER_TYPES
    )


@sellers.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):
    seller = Seller.query.get_or_404(id)
    if request.method == "POST":
        photo = seller.profile_photo
        db.session.delete(seller)
        db.session.commit()
        record_audit(
            "Delete",
            "Marketplace",
            f"Seller {seller.seller_number} deleted",
            "Seller",
            seller.id,
        )
        _remove_photo(photo)
        flash("Seller deleted successfully.", "success")
        return redirect(url_for("sellers.index"))
    return render_template("sellers/delete.html", seller=seller)
