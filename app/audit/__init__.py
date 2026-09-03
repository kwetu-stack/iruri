from flask import Blueprint

audit = Blueprint("audit", __name__, url_prefix="/audit")

from app.audit import routes
