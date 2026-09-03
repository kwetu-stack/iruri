from flask import Blueprint

buyers = Blueprint("buyers", __name__, url_prefix="/buyers")

from app.buyers.models import Buyer
from app.buyers import routes
