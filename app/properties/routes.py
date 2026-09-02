from flask import render_template
from flask_login import login_required

from app.properties import properties


@properties.route("/")
@login_required
def index():

    return render_template(
        "properties/index.html"
    )