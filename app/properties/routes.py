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
