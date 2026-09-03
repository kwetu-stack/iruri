from flask import Blueprint

properties = Blueprint("properties", __name__, url_prefix="/properties")

# Import models first so SQLAlchemy registers them
from app.properties.models import Property
from app.properties.image_models import PropertyImage

# Import routes after blueprint creation
from app.properties import routes
