from flask import Blueprint

developers = Blueprint("developers", __name__, url_prefix="/developers")

from app.developers.models import Developer
from app.developers import routes
