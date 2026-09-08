from flask import Blueprint

media = Blueprint("media", __name__, url_prefix="/media")

from app.media.models import MediaAsset
from app.media import routes
