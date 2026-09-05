from flask import Blueprint

leads = Blueprint("leads", __name__, url_prefix="/leads")

from app.leads.models import Lead

from app.leads import routes  # noqa: E402,F401
