from flask import Blueprint

developers = Blueprint("developers", __name__, url_prefix="/admin/developers")

from app.developers.models import Developer
from app.developers import routes
