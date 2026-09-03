import os
import re
import uuid
import math
from datetime import datetime
from urllib.parse import urlparse

from flask import (
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
)

from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app.sellers.models import Seller
from app.developers.models import Developer
from app.agents.models import Agent
from app.buyers.models import Buyer
from app.audit.service import record_audit


from app.extensions import db
from app.properties import properties
from app.properties.image_models import PropertyImage
from app.properties.models import (
    Amenity,
    Property,
    PropertyDocument,
    PropertyFeature,
    PropertyFloorPlan,
    PropertyVideo,
    SavedProperty,
)
from app.transactions.models import PropertyTransaction

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024
ALLOWED_FLOOR_PLAN_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FLOOR_PLAN_SIZE = 20 * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
MAX_VIDEO_SIZE = 100 * 1024 * 1024
DOCUMENT_TYPES = (
    "Title Deed",
    "Lease Agreement",
    "Sale Agreement",
    "Survey Map",
    "Mutation Form",
    "Valuation Report",
    "Architectural Drawing",
    "Structural Drawing",
    "Occupation Certificate",
    "NEMA Approval",
    "County Approval",
    "Utility Bill",
    "ID Copy",
    "KRA PIN",
    "Other",
)


def _current_buyer():
    if not current_user.is_authenticated or not current_user.email:
        return None
    return Buyer.query.filter_by(email=current_user.email).first()


def _is_admin():
    return (current_user.role or "").lower() in {"admin", "administrator"}


def _relationship_options():
    return {
        "sellers": Seller.query.order_by(Seller.seller_number).all(),
        "developers": Developer.query.order_by(Developer.developer_number).all(),
        "agents": Agent.query.order_by(Agent.agent_number).all(),
        "amenities": Amenity.query.order_by(Amenity.category, Amenity.name).all(),
        "features": PropertyFeature.query.order_by(
            PropertyFeature.category, PropertyFeature.name
        ).all(),
    }


def _render_property_form(template, property=None):
    context = _relationship_options()
    if property is not None:
        context["property"] = property
    return render_template(template, **context)


def _image_upload_folder():
    folder = os.path.join(
        current_app.root_path,
        "static",
        "uploads",
        "properties",
    )
    os.makedirs(folder, exist_ok=True)
    return folder


def _document_upload_folder():
    folder = os.path.join(
        current_app.root_path, "static", "uploads", "property_documents"
    )
    os.makedirs(folder, exist_ok=True)
    return folder


def _floor_plan_upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "floor_plans")
    os.makedirs(folder, exist_ok=True)
    return folder


def _has_allowed_extension(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _has_allowed_document_extension(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS
    )


def _has_allowed_floor_plan_extension(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_FLOOR_PLAN_EXTENSIONS
    )


def _has_allowed_video_extension(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
    )


def _is_supported_external_url(value):
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme == "https" and hostname in {
        "youtube.com",
        "youtu.be",
        "vimeo.com",
    }


def _sanitize_floor_name(value):
    return re.sub(r"[^A-Za-z0-9]+", "", value.strip()) or "FloorPlan"


def _file_size(uploaded_file):
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    return size


def _selected_amenities():
    amenity_ids = {
        int(value) for value in request.form.getlist("amenity_ids") if value.isdigit()
    }
    return (
        Amenity.query.filter(Amenity.id.in_(amenity_ids)).all() if amenity_ids else []
    )


def _selected_features():
    feature_ids = {
        int(value) for value in request.form.getlist("feature_ids") if value.isdigit()
    }
    return (
        PropertyFeature.query.filter(PropertyFeature.id.in_(feature_ids)).all()
        if feature_ids
        else []
    )


def _location_values():
    values = {
        "county": request.form.get("county", "").strip() or None,
        "town": request.form.get("town", "").strip() or None,
        "estate": request.form.get("estate", "").strip() or None,
        "neighbourhood": request.form.get("neighbourhood", "").strip() or None,
        "landmark": request.form.get("landmark", "").strip() or None,
        "postal_code": request.form.get("postal_code", "").strip() or None,
        "google_map_url": request.form.get("google_map_url", "").strip() or None,
    }

    for field, minimum, maximum in (
        ("latitude", -90, 90),
        ("longitude", -180, 180),
    ):
        raw_value = request.form.get(field, "").strip()
        if not raw_value:
            values[field] = None
            continue
        try:
            value = float(raw_value)
        except ValueError:
            raise ValueError(f"{field.capitalize()} must be numeric.")
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(
                f"{field.capitalize()} must be between {minimum} and {maximum}."
            )
        values[field] = value

    return values


def _amenity_form(template, amenity=None):
    return render_template(template, amenity=amenity)


@properties.route("/amenities")
@login_required
def amenities_index():
    amenities = Amenity.query.order_by(Amenity.category, Amenity.name).all()
    return render_template("amenities/index.html", amenities=amenities)


@properties.route("/amenities/create", methods=["GET", "POST"])
@login_required
def amenities_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Amenity name is required.", "danger")
            return _amenity_form("amenities/create.html")
        if Amenity.query.filter(db.func.lower(Amenity.name) == name.lower()).first():
            flash("An amenity with that name already exists.", "danger")
            return _amenity_form("amenities/create.html")

        db.session.add(
            Amenity(
                name=name,
                icon=request.form.get("icon", "").strip() or None,
                category=request.form.get("category", "").strip() or None,
            )
        )
        db.session.commit()
        record_audit(
            "Create",
            "Marketplace",
            f"Property {property.listing_number} created",
            "Property",
            property.id,
        )
        flash("Amenity created successfully.", "success")
        return redirect(url_for("properties.amenities_index"))

    return _amenity_form("amenities/create.html")


@properties.route("/amenities/<int:id>/edit", methods=["GET", "POST"])
@login_required
def amenities_edit(id):
    amenity = Amenity.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duplicate = Amenity.query.filter(
            db.func.lower(Amenity.name) == name.lower(), Amenity.id != amenity.id
        ).first()
        if not name:
            flash("Amenity name is required.", "danger")
            return _amenity_form("amenities/edit.html", amenity)
        if duplicate:
            flash("An amenity with that name already exists.", "danger")
            return _amenity_form("amenities/edit.html", amenity)

        amenity.name = name
        amenity.icon = request.form.get("icon", "").strip() or None
        amenity.category = request.form.get("category", "").strip() or None
        db.session.commit()
        record_audit(
            "Update",
            "Marketplace",
            f"Property {property.listing_number} updated",
            "Property",
            property.id,
        )
        flash("Amenity updated successfully.", "success")
        return redirect(url_for("properties.amenities_index"))

    return _amenity_form("amenities/edit.html", amenity)


@properties.route("/amenities/<int:id>/delete", methods=["GET", "POST"])
@login_required
def amenities_delete(id):
    amenity = Amenity.query.get_or_404(id)
    if request.method == "POST":
        db.session.delete(amenity)
        db.session.commit()
        flash("Amenity deleted successfully.", "success")
        return redirect(url_for("properties.amenities_index"))
    return render_template("amenities/delete.html", amenity=amenity)


def _feature_form(template, feature=None):
    return render_template(template, feature=feature)


@properties.route("/features")
@login_required
def features_index():
    features = PropertyFeature.query.order_by(
        PropertyFeature.category, PropertyFeature.name
    ).all()
    return render_template("property_features/index.html", features=features)


@properties.route("/features/create", methods=["GET", "POST"])
@login_required
def features_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Feature name is required.", "danger")
            return _feature_form("property_features/create.html")
        if PropertyFeature.query.filter(
            db.func.lower(PropertyFeature.name) == name.lower()
        ).first():
            flash("A feature with that name already exists.", "danger")
            return _feature_form("property_features/create.html")

        db.session.add(
            PropertyFeature(
                name=name,
                category=request.form.get("category", "").strip() or None,
            )
        )
        db.session.commit()
        flash("Feature created successfully.", "success")
        return redirect(url_for("properties.features_index"))

    return _feature_form("property_features/create.html")


@properties.route("/features/<int:id>/edit", methods=["GET", "POST"])
@login_required
def features_edit(id):
    feature = PropertyFeature.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duplicate = PropertyFeature.query.filter(
            db.func.lower(PropertyFeature.name) == name.lower(),
            PropertyFeature.id != feature.id,
        ).first()
        if not name:
            flash("Feature name is required.", "danger")
            return _feature_form("property_features/edit.html", feature)
        if duplicate:
            flash("A feature with that name already exists.", "danger")
            return _feature_form("property_features/edit.html", feature)

        feature.name = name
        feature.category = request.form.get("category", "").strip() or None
        db.session.commit()
        flash("Feature updated successfully.", "success")
        return redirect(url_for("properties.features_index"))

    return _feature_form("property_features/edit.html", feature)


@properties.route("/features/<int:id>/delete", methods=["GET", "POST"])
@login_required
def features_delete(id):
    feature = PropertyFeature.query.get_or_404(id)
    if request.method == "POST":
        db.session.delete(feature)
        db.session.commit()
        flash("Feature deleted successfully.", "success")
        return redirect(url_for("properties.features_index"))
    return render_template("property_features/delete.html", feature=feature)


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
    buyer = _current_buyer()
    saved_property = (
        SavedProperty.query.filter_by(
            buyer_id=buyer.id, property_id=property.id
        ).first()
        if buyer
        else None
    )
    offer_counts = {
        status: sum(offer.status == status for offer in property.offers)
        for status in (
            "Pending",
            "Under Review",
            "Counter Offered",
            "Accepted",
            "Rejected",
        )
    }
    negotiation_count = sum(len(offer.negotiations) for offer in property.offers)

    return render_template(
        "properties/details.html",
        property=property,
        saved_property=saved_property,
        current_buyer=buyer,
        offer_counts=offer_counts,
        negotiation_count=negotiation_count,
    )


@properties.route("/<int:id>/save", methods=["POST"])
@login_required
def save_property(id):
    property = Property.query.get_or_404(id)
    buyer = _current_buyer()
    if not buyer:
        flash("A buyer profile is required to save properties.", "danger")
        return redirect(url_for("properties.details", id=property.id))

    saved_property = SavedProperty.query.filter_by(
        buyer_id=buyer.id, property_id=property.id
    ).first()
    if saved_property:
        db.session.delete(saved_property)
        flash("Property removed from saved properties.", "success")
    else:
        db.session.add(SavedProperty(buyer_id=buyer.id, property_id=property.id))
        flash("Property saved successfully.", "success")
    db.session.commit()
    return redirect(url_for("properties.details", id=property.id))


@properties.route("/<int:id>/remove-saved", methods=["POST"])
@login_required
def remove_saved_property(id):
    property = Property.query.get_or_404(id)
    buyer_id = request.form.get("buyer_id", type=int)
    buyer = _current_buyer()
    if buyer_id and (not buyer or buyer.id != buyer_id):
        buyer = Buyer.query.get_or_404(buyer_id)
    if not buyer:
        flash("A buyer profile is required to remove saved properties.", "danger")
        return redirect(url_for("properties.details", id=property.id))

    saved_property = SavedProperty.query.filter_by(
        buyer_id=buyer.id, property_id=property.id
    ).first()
    if saved_property:
        db.session.delete(saved_property)
        db.session.commit()
        flash("Property removed from saved properties.", "success")
    return redirect(url_for("buyers.details", id=buyer.id))


def _video_upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "property_videos")
    os.makedirs(folder, exist_ok=True)
    return folder


@properties.route("/<int:id>/videos/upload", methods=["GET", "POST"])
@login_required
def upload_video(id):
    property = Property.query.get_or_404(id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip() or None
        video_type = request.form.get("video_type", "").strip()
        uploaded_file = request.files.get("file")
        external_url = request.form.get("external_url", "").strip()

        if not title:
            flash("Video title is required.", "danger")
        elif video_type not in {"upload", "external"}:
            flash("Select a valid video type.", "danger")
        elif video_type == "upload" and (
            not uploaded_file or not uploaded_file.filename
        ):
            flash("Select a video file to upload.", "danger")
        elif video_type == "upload" and not _has_allowed_video_extension(
            uploaded_file.filename
        ):
            flash("Only MP4, WEBM, and MOV videos are allowed.", "danger")
        elif video_type == "upload" and _file_size(uploaded_file) > MAX_VIDEO_SIZE:
            flash("Videos must be 100 MB or smaller.", "danger")
        elif video_type == "external" and not _is_supported_external_url(external_url):
            flash("Enter a valid HTTPS YouTube or Vimeo URL.", "danger")
        else:
            next_order = (
                db.session.query(db.func.max(PropertyVideo.display_order))
                .filter_by(property_id=property.id)
                .scalar()
                or 0
            ) + 1
            saved_path = None
            file_name = None
            file_path = None

            if video_type == "upload":
                original_filename = secure_filename(uploaded_file.filename)
                extension = original_filename.rsplit(".", 1)[1].lower()
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                property_number = secure_filename(property.listing_number) or "property"
                file_name = f"{property_number}_{timestamp}.{extension}"
                saved_path = os.path.join(_video_upload_folder(), file_name)
                uploaded_file.save(saved_path)
                file_path = os.path.join("uploads", "property_videos", file_name)

            video = PropertyVideo(
                property_id=property.id,
                title=title,
                description=description,
                video_type=video_type,
                file_name=file_name,
                file_path=file_path,
                external_url=external_url if video_type == "external" else None,
                display_order=next_order,
            )
            try:
                db.session.add(video)
                db.session.commit()
            except Exception:
                db.session.rollback()
                if saved_path and os.path.exists(saved_path):
                    os.remove(saved_path)
                raise

            flash("Property video saved successfully.", "success")
            return redirect(url_for("properties.details", id=property.id))

    return render_template("property_videos/upload.html", property=property)


@properties.route("/videos/<int:id>/watch")
@login_required
def watch_video(id):
    video = PropertyVideo.query.get_or_404(id)
    if video.video_type == "external":
        return redirect(video.external_url)
    return send_from_directory(_video_upload_folder(), video.file_name)


@properties.route("/videos/<int:id>/delete", methods=["POST"])
@login_required
def delete_video(id):
    video = PropertyVideo.query.get_or_404(id)
    property_id = video.property_id
    file_path = (
        os.path.join(_video_upload_folder(), video.file_name)
        if video.video_type == "upload" and video.file_name
        else None
    )
    db.session.delete(video)
    db.session.commit()
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    flash("Property video deleted successfully.", "success")
    return redirect(url_for("properties.details", id=property_id))


def _document_form_context(property=None):
    return {
        "property": property,
        "properties": Property.query.order_by(Property.title).all(),
        "document_types": DOCUMENT_TYPES,
    }


@properties.route("/documents")
@login_required
def documents():
    property_id = request.args.get("property_id", type=int)
    query = PropertyDocument.query
    if property_id:
        query = query.filter_by(property_id=property_id)
    documents_list = query.order_by(PropertyDocument.uploaded_at.desc()).all()
    return render_template(
        "property_documents/index.html",
        documents=documents_list,
        selected_property_id=property_id,
    )


@properties.route("/documents/upload", methods=["GET", "POST"])
@login_required
def upload_document():
    selected_property_id = request.args.get("property_id", type=int)
    selected_property = (
        Property.query.get(selected_property_id) if selected_property_id else None
    )
    if request.method == "POST":
        property_id = request.form.get("property_id", "").strip()
        document_type = request.form.get("document_type", "").strip()
        uploaded_file = request.files.get("file")
        selected_property = (
            Property.query.get(int(property_id)) if property_id.isdigit() else None
        )

        if not selected_property:
            flash("A valid property is required.", "danger")
        elif document_type not in DOCUMENT_TYPES:
            flash("Select a valid document type.", "danger")
        elif not uploaded_file or not uploaded_file.filename:
            flash("Select a document to upload.", "danger")
        elif not _has_allowed_document_extension(uploaded_file.filename):
            flash("Only PDF, JPG, JPEG, and PNG documents are allowed.", "danger")
        elif _file_size(uploaded_file) > MAX_DOCUMENT_SIZE:
            flash("Documents must be 20 MB or smaller.", "danger")
        else:
            original_filename = secure_filename(uploaded_file.filename)
            extension = original_filename.rsplit(".", 1)[1].lower()
            stored_filename = f"{uuid.uuid4().hex}.{extension}"
            upload_folder = _document_upload_folder()
            file_path = os.path.join(upload_folder, stored_filename)
            uploaded_file.save(file_path)
            document = PropertyDocument(
                property_id=selected_property.id,
                document_type=document_type,
                document_name=original_filename,
                file_name=stored_filename,
                file_path=os.path.join(
                    "uploads", "property_documents", stored_filename
                ),
                file_size=os.path.getsize(file_path),
                file_extension=extension,
                uploaded_by=(
                    current_user.id if current_user.is_authenticated else None
                ),
                notes=request.form.get("notes", "").strip() or None,
            )
            try:
                db.session.add(document)
                db.session.commit()
            except Exception:
                db.session.rollback()
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise
            flash("Document uploaded successfully.", "success")
            return redirect(url_for("properties.details", id=selected_property.id))

    return render_template(
        "property_documents/upload.html",
        **_document_form_context(selected_property),
    )


@properties.route("/documents/<int:id>/download")
@login_required
def download_document(id):
    document = PropertyDocument.query.get_or_404(id)
    return send_from_directory(
        _document_upload_folder(),
        document.file_name,
        as_attachment=True,
        download_name=document.document_name,
    )


@properties.route("/documents/<int:id>/delete", methods=["POST"])
@login_required
def delete_document(id):
    document = PropertyDocument.query.get_or_404(id)
    property_id = document.property_id
    file_path = os.path.join(_document_upload_folder(), document.file_name)
    db.session.delete(document)
    db.session.commit()
    if os.path.exists(file_path):
        os.remove(file_path)
    flash("Document deleted successfully.", "success")
    return redirect(url_for("properties.details", id=property_id))


@properties.route("/<int:id>/floor-plans")
@login_required
def floor_plans(id):
    property = Property.query.get_or_404(id)
    floor_plans_list = (
        PropertyFloorPlan.query.filter_by(property_id=property.id)
        .order_by(
            PropertyFloorPlan.display_order.asc(), PropertyFloorPlan.uploaded_at.asc()
        )
        .all()
    )
    return render_template(
        "property_floor_plans/index.html",
        property=property,
        floor_plans=floor_plans_list,
    )


@properties.route("/<int:id>/floor-plans/upload", methods=["GET", "POST"])
@login_required
def upload_floor_plan(id):
    property = Property.query.get_or_404(id)

    if request.method == "POST":
        floor_name = request.form.get("floor_name", "").strip()
        description = request.form.get("description", "").strip()
        uploaded_file = request.files.get("file")

        if not property:
            flash("A valid property is required.", "danger")
        elif not floor_name:
            flash("Floor name is required.", "danger")
        elif not uploaded_file or not uploaded_file.filename:
            flash("Select a floor plan file to upload.", "danger")
        elif not _has_allowed_floor_plan_extension(uploaded_file.filename):
            flash("Only JPG, JPEG, PNG, and PDF floor plans are allowed.", "danger")
        elif _file_size(uploaded_file) > MAX_FLOOR_PLAN_SIZE:
            flash("Floor plans must be 20 MB or smaller.", "danger")
        else:
            original_filename = secure_filename(uploaded_file.filename)
            extension = original_filename.rsplit(".", 1)[1].lower()
            timestamp = (
                __import__("datetime").datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            )
            safe_property_number = property.listing_number.replace(" ", "")
            safe_floor_name = _sanitize_floor_name(floor_name)
            stored_filename = (
                f"{safe_property_number}_{safe_floor_name}_{timestamp}.{extension}"
            )
            file_path = os.path.join(_floor_plan_upload_folder(), stored_filename)

            uploaded_file.save(file_path)

            next_order = (
                db.session.query(db.func.max(PropertyFloorPlan.display_order))
                .filter_by(property_id=property.id)
                .scalar()
                or 0
            ) + 1

            floor_plan = PropertyFloorPlan(
                property_id=property.id,
                floor_name=floor_name,
                description=description or None,
                file_name=stored_filename,
                file_path=os.path.join("uploads", "floor_plans", stored_filename),
                file_extension=extension,
                file_size=os.path.getsize(file_path),
                display_order=next_order,
            )

            try:
                db.session.add(floor_plan)
                db.session.commit()
            except Exception:
                db.session.rollback()
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise

            flash("Floor plan uploaded successfully.", "success")
            return redirect(url_for("properties.details", id=property.id))

    return render_template(
        "property_floor_plans/upload.html",
        property=property,
    )


@properties.route("/floor-plans/<int:id>/download")
@login_required
def download_floor_plan(id):
    floor_plan = PropertyFloorPlan.query.get_or_404(id)
    download_name = (
        f"{_sanitize_floor_name(floor_plan.floor_name)}.{floor_plan.file_extension}"
    )
    return send_from_directory(
        _floor_plan_upload_folder(),
        floor_plan.file_name,
        as_attachment=True,
        download_name=download_name,
    )


@properties.route("/floor-plans/<int:id>/delete", methods=["POST"])
@login_required
def delete_floor_plan(id):
    floor_plan = PropertyFloorPlan.query.get_or_404(id)
    property_id = floor_plan.property_id
    file_path = os.path.join(_floor_plan_upload_folder(), floor_plan.file_name)

    db.session.delete(floor_plan)
    db.session.commit()

    if os.path.exists(file_path):
        os.remove(file_path)

    flash("Floor plan deleted successfully.", "success")
    return redirect(url_for("properties.details", id=property_id))


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
        seller_id = request.form.get("seller_id", "").strip()
        developer_id = request.form.get("developer_id", "").strip()
        agent_id = request.form.get("agent_id", "").strip()
        seller = Seller.query.get(int(seller_id)) if seller_id.isdigit() else None
        developer = (
            Developer.query.get(int(developer_id)) if developer_id.isdigit() else None
        )
        agent = Agent.query.get(int(agent_id)) if agent_id.isdigit() else None

        if not seller:
            flash("A seller is required.", "danger")
            return _render_property_form("properties/create.html")
        if developer_id and not developer:
            flash("The selected developer is invalid.", "danger")
            return _render_property_form("properties/create.html")
        if agent_id and not agent:
            flash("The selected agent is invalid.", "danger")
            return _render_property_form("properties/create.html")

        try:
            location_values = _location_values()
        except ValueError as error:
            flash(str(error), "danger")
            return _render_property_form("properties/create.html")

        property = Property(
            listing_number="TEMP",
            seller_id=seller.id,
            developer_id=developer.id if developer else None,
            agent_id=agent.id if agent else None,
            title=request.form["title"],
            description=request.form["description"],
            property_type=request.form["property_type"],
            listing_type=request.form["listing_type"],
            price=float(request.form["price"]),
            **location_values,
            amenities=_selected_amenities(),
            features=_selected_features(),
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

    return _render_property_form("properties/create.html")


@properties.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):

    property = Property.query.get_or_404(id)
    if (
        property.status == "Sold"
        or PropertyTransaction.query.filter_by(
            property_id=property.id, transaction_status="Completed"
        ).first()
    ):
        if not _is_admin():
            flash("Sold properties are read-only.", "danger")
            return redirect(url_for("properties.details", id=property.id))

    if request.method == "POST":
        seller_id = request.form.get("seller_id", "").strip()
        developer_id = request.form.get("developer_id", "").strip()
        agent_id = request.form.get("agent_id", "").strip()
        seller = Seller.query.get(int(seller_id)) if seller_id.isdigit() else None
        developer = (
            Developer.query.get(int(developer_id)) if developer_id.isdigit() else None
        )
        agent = Agent.query.get(int(agent_id)) if agent_id.isdigit() else None

        if not seller:
            flash("A seller is required.", "danger")
            return _render_property_form("properties/edit.html", property)
        if developer_id and not developer:
            flash("The selected developer is invalid.", "danger")
            return _render_property_form("properties/edit.html", property)
        if agent_id and not agent:
            flash("The selected agent is invalid.", "danger")
            return _render_property_form("properties/edit.html", property)

        title = request.form.get("title", "").strip()
        property_type = request.form.get("property_type", "").strip()
        listing_type = request.form.get("listing_type", "").strip()
        price_value = request.form.get("price", "").strip()

        if not title or not property_type or not listing_type or not price_value:
            flash(
                "Title, property type, listing type, and price are required.",
                "danger",
            )
            return _render_property_form("properties/edit.html", property)

        try:
            price = float(price_value)
        except ValueError:
            flash("Price must be numeric.", "danger")
            return _render_property_form("properties/edit.html", property)

        property.title = title
        property.description = request.form.get("description", "").strip()
        property.property_type = property_type
        property.listing_type = listing_type
        property.seller_id = seller.id
        property.developer_id = developer.id if developer else None
        property.agent_id = agent.id if agent else None
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
            return _render_property_form("properties/edit.html", property)

        try:
            location_values = _location_values()
        except ValueError as error:
            flash(str(error), "danger")
            return _render_property_form("properties/edit.html", property)

        for field, value in location_values.items():
            setattr(property, field, value)

        property.status = request.form.get("status", "").strip() or None
        property.featured = request.form.get("featured") == "on"
        property.verified = request.form.get("verified") == "on"
        property.amenities = _selected_amenities()
        property.features = _selected_features()

        db.session.commit()

        flash("Property updated successfully.", "success")
        return redirect(url_for("properties.details", id=property.id))

    return _render_property_form("properties/edit.html", property)


@properties.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):

    property = Property.query.get_or_404(id)

    if request.method == "POST":
        db.session.delete(property)
        db.session.commit()
        record_audit(
            "Delete",
            "Marketplace",
            f"Property {property.listing_number} deleted",
            "Property",
            property.id,
        )

        flash("Property deleted successfully.", "success")
        return redirect(url_for("properties.index"))

    return render_template("properties/delete.html", property=property)
