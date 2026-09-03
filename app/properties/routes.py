import os
import uuid

from flask import (
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_login import login_required

from app.extensions import db
from app.properties import properties
from app.properties.image_models import PropertyImage
from app.properties.models import Property

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _image_upload_folder():
    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "properties",
    )
    os.makedirs(folder, exist_ok=True)
    return folder


def _has_allowed_extension(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _file_size(uploaded_file):
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    return size


@properties.route("/")
@login_required
def index():

    properties_list = Property.query.order_by(Property.created_at.desc()).all()

    return render_template(
        "properties/index.html",
        properties=properties_list,
    )


@properties.route("/<int:id>")
@login_required
def details(id):

    property = Property.query.get_or_404(id)

    return render_template(
        "properties/details.html",
        property=property,
    )


@properties.route("/<int:id>/images")
@login_required
def images(id):
    property = Property.query.get_or_404(id)
    property_images = (
        PropertyImage.query.filter_by(property_id=property.id)
        .order_by(
            PropertyImage.display_order.asc(),
            PropertyImage.created_at.asc(),
        )
        .all()
    )

    return render_template(
        "properties/images.html",
        property=property,
        images=property_images,
    )


@properties.route("/<int:id>/images/upload", methods=["GET", "POST"])
@login_required
def upload_images(id):
    property = Property.query.get_or_404(id)

    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        valid_files = []

        for uploaded_file in uploaded_files:
            if not uploaded_file or not uploaded_file.filename:
                continue

            if not _has_allowed_extension(uploaded_file.filename):
                flash("Only JPG, JPEG, PNG, and WEBP images are allowed.", "danger")
                return render_template(
                    "properties/images.html", property=property, images=property.images
                )

            if _file_size(uploaded_file) > MAX_IMAGE_SIZE:
                flash("Each image must be 10 MB or smaller.", "danger")
                return render_template(
                    "properties/images.html", property=property, images=property.images
                )

            valid_files.append(uploaded_file)

        if not valid_files:
            flash("Select at least one image to upload.", "danger")
            return redirect(url_for("properties.upload_images", id=property.id))

        upload_folder = _image_upload_folder()
        next_order = (
            db.session.query(db.func.max(PropertyImage.display_order))
            .filter_by(property_id=property.id)
            .scalar()
        )
        next_order = (next_order or 0) + 1
        saved_paths = []

        try:
            for uploaded_file in valid_files:
                original_filename = uploaded_file.filename
                extension = original_filename.rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{extension}"
                file_path = os.path.join(upload_folder, filename)
                uploaded_file.save(file_path)
                saved_paths.append(file_path)
                db.session.add(
                    PropertyImage(
                        property_id=property.id,
                        filename=filename,
                        original_filename=original_filename,
                        display_order=next_order,
                    )
                )
                next_order += 1

            db.session.commit()
        except Exception:
            db.session.rollback()
            for file_path in saved_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
            raise

        flash("Images uploaded successfully.", "success")
        return redirect(url_for("properties.images", id=property.id))

    property_images = (
        PropertyImage.query.filter_by(property_id=property.id)
        .order_by(
            PropertyImage.display_order.asc(),
            PropertyImage.created_at.asc(),
        )
        .all()
    )
    return render_template(
        "properties/images.html",
        property=property,
        images=property_images,
    )


@properties.route("/image/<int:id>/delete", methods=["POST"])
@login_required
def delete_image(id):
    image = PropertyImage.query.get_or_404(id)
    property_id = image.property_id
    file_path = os.path.join(_image_upload_folder(), image.filename)

    db.session.delete(image)
    db.session.commit()

    if os.path.exists(file_path):
        os.remove(file_path)

    flash("Image deleted successfully.", "success")
    return redirect(url_for("properties.images", id=property_id))


@properties.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        property = Property(
            listing_number="TEMP",
            title=request.form["title"],
            description=request.form["description"],
            property_type=request.form["property_type"],
            listing_type=request.form["listing_type"],
            price=float(request.form["price"]),
            county=request.form["county"],
        )

        db.session.add(property)
        db.session.flush()

        property.listing_number = f"IRR-2026-{property.id:06d}"

        db.session.commit()

        flash(
            "Property added successfully.",
            "success",
        )

        return redirect(url_for("properties.index"))

    return render_template("properties/create.html")


@properties.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):

    property = Property.query.get_or_404(id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        property_type = request.form.get("property_type", "").strip()
        listing_type = request.form.get("listing_type", "").strip()
        price_value = request.form.get("price", "").strip()

        if not title or not property_type or not listing_type or not price_value:
            flash(
                "Title, property type, listing type, and price are required.",
                "danger",
            )
            return render_template("properties/edit.html", property=property)

        try:
            price = float(price_value)
        except ValueError:
            flash("Price must be numeric.", "danger")
            return render_template("properties/edit.html", property=property)

        property.title = title
        property.description = request.form.get("description", "").strip()
        property.property_type = property_type
        property.listing_type = listing_type
        property.price = price
        property.currency = request.form.get("currency", "").strip() or None
        property.county = request.form.get("county", "").strip() or None
        property.town = request.form.get("town", "").strip() or None
        property.estate = request.form.get("estate", "").strip() or None
        property.address = request.form.get("address", "").strip() or None

        try:
            property.bedrooms = int(request.form.get("bedrooms", ""))
            property.bathrooms = int(request.form.get("bathrooms", ""))
            property.parking = int(request.form.get("parking", ""))
            property.floor_area = (
                float(request.form.get("floor_area", ""))
                if request.form.get("floor_area", "").strip()
                else None
            )
            property.land_size = (
                float(request.form.get("land_size", ""))
                if request.form.get("land_size", "").strip()
                else None
            )
        except ValueError:
            flash(
                "Bedrooms, bathrooms, and parking must be whole numbers. Floor area and land size must be numeric.",
                "danger",
            )
            return render_template("properties/edit.html", property=property)

        property.status = request.form.get("status", "").strip() or None
        property.featured = request.form.get("featured") == "on"
        property.verified = request.form.get("verified") == "on"

        db.session.commit()

        flash("Property updated successfully.", "success")
        return redirect(url_for("properties.details", id=property.id))

    return render_template("properties/edit.html", property=property)


@properties.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):

    property = Property.query.get_or_404(id)

    if request.method == "POST":
        db.session.delete(property)
        db.session.commit()

        flash("Property deleted successfully.", "success")
        return redirect(url_for("properties.index"))

    return render_template("properties/delete.html", property=property)
