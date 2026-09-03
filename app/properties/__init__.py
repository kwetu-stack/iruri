from flask import Blueprint
from sqlalchemy.exc import OperationalError

from app.extensions import db

properties = Blueprint("properties", __name__, url_prefix="/properties")

# Import models first so SQLAlchemy registers them
from app.properties.models import Amenity, Property
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


def seed_default_amenities():
    try:
        if Amenity.query.first() is not None:
            return
    except OperationalError:
        db.session.rollback()
        return

    db.session.add_all(Amenity(name=name) for name in DEFAULT_AMENITIES)
    db.session.commit()


# Import routes after blueprint creation
from app.properties import routes
