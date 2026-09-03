from flask import Blueprint

agencies = Blueprint("agencies", __name__, url_prefix="/agencies")

from app.agencies.models import Agency
from app.agencies import routes
