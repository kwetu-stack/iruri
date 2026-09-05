from flask import Blueprint

public = Blueprint("public", __name__, template_folder="../templates/public")

from app.public import routes  # noqa: E402,F401
