from flask import Blueprint

offers = Blueprint("offers", __name__, url_prefix="/offers")

from app.offers import routes  # noqa: E402,F401
