from flask import Flask, redirect, render_template, url_for
from flask_login import login_required
from app.dashboard import dashboard


from config import Config
from app.extensions import db, migrate, login_manager
from app.auth import auth
from app.properties import properties, seed_default_amenities
from app.agents import agents
from app.agencies import agencies
from app.developers import developers
from app.sellers import sellers
from app.buyers import buyers
from app.properties.models import Amenity

import app.models


def create_app():
    """Application Factory."""

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from flask import redirect, url_for

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    @app.route("/amenities")
    @app.route("/amenities/", strict_slashes=False)
    @login_required
    def amenities_root():
        amenities = Amenity.query.order_by(Amenity.category, Amenity.name).all()
        return render_template("amenities/index.html", amenities=amenities)

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(properties)
    app.register_blueprint(agents)
    app.register_blueprint(agencies)
    app.register_blueprint(developers)
    app.register_blueprint(sellers)
    app.register_blueprint(buyers)

    with app.app_context():
        seed_default_amenities()

    return app
