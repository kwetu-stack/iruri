from flask import Blueprint

activities = Blueprint("activities", __name__, url_prefix="/activities")

from app.activities import routes
