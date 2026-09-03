from flask import Blueprint

viewings = Blueprint("viewings", __name__, url_prefix="/viewings")

from app.viewings.models import ViewingRequest
from app.viewings import routes
