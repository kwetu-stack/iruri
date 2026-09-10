from flask import Blueprint

agencies = Blueprint("agencies", __name__, url_prefix="/admin/agencies")

from app.agencies.models import Agency
from app.agencies import routes
