from flask import Blueprint
from sqlalchemy.exc import OperationalError

from app.extensions import db

properties = Blueprint("properties", __name__, url_prefix="/properties")

# Import models first so SQLAlchemy registers them
from app.properties.models import Amenity, Property, PropertyDocument, PropertyFeature
from app.properties.image_models import PropertyImage

DEFAULT_AMENITIES = (
    "Swimming Pool",
    "Borehole",
    "Gym",
    "Lift",
    "CCTV",
    "Fibre Internet",
    "Solar Power",
    "Garden",
    "Electric Fence",
    "Cabro Parking",
    "Backup Generator",
    "Balcony",
    "Air Conditioning",
    "Water Tank",
    "Servant Quarter",
    "Children's Play Area",
)

DEFAULT_FEATURES = {
    "Interior": (
        "Ensuite Bedrooms",
        "Walk-in Closet",
        "Fitted Kitchen",
        "Pantry",
        "Laundry Area",
        "Home Office",
        "Air Conditioning",
    ),
    "Exterior": ("Balcony", "Terrace", "Garden", "Rooftop", "Perimeter Wall"),
    "Construction": (
        "Newly Built",
        "Newly Renovated",
        "Modern Design",
        "Smart Home",
        "Energy Efficient",
    ),
    "Ownership": ("Freehold", "Leasehold"),
    "Location": (
        "Corner Plot",
        "Sea View",
        "Mountain View",
        "Lake View",
        "Gated Community",
    ),
}


def seed_default_amenities():
    try:
        if Amenity.query.first() is not None:
            return
    except OperationalError:
        db.session.rollback()
        return

    db.session.add_all(Amenity(name=name) for name in DEFAULT_AMENITIES)
    db.session.commit()


def seed_default_features():
    try:
        if PropertyFeature.query.first() is not None:
            return
    except OperationalError:
        db.session.rollback()
        return

    db.session.add_all(
        PropertyFeature(name=name, category=category)
        for category, names in DEFAULT_FEATURES.items()
        for name in names
    )
    db.session.commit()


# Import routes after blueprint creation
from app.properties import routes
