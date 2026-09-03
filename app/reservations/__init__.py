from flask import Blueprint

reservations = Blueprint("reservations", __name__, url_prefix="/reservations")

from app.reservations import routes  # noqa: E402,F401
