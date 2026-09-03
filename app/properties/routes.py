from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_login import login_required

from app.extensions import db
from app.properties import properties
from app.properties.models import Property


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
