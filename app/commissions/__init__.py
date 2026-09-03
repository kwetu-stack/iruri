from flask import Blueprint

commissions = Blueprint("commissions", __name__, url_prefix="/commissions")

from app.commissions import routes  # noqa: E402,F401
