from flask import Blueprint

sale_agreements = Blueprint("sale_agreements", __name__, url_prefix="/sale-agreements")

from app.sale_agreements import routes  # noqa: E402,F401
