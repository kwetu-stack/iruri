from flask import Blueprint

developments = Blueprint("developments", __name__, url_prefix="/developments")

from app.developments.models import Development
from app.developments import routes
