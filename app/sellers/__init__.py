from flask import Blueprint

sellers = Blueprint("sellers", __name__, url_prefix="/sellers")

from app.sellers.models import Seller
from app.sellers import routes
