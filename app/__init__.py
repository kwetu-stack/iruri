from flask import Flask, redirect, url_for
from app.dashboard import dashboard


from config import Config
from app.extensions import db, migrate, login_manager
from app.auth import auth
from app.properties import properties
from app.agents import agents

import app.models


def create_app():
    """Application Factory."""

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()

    from flask import redirect, url_for

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(properties)
    app.register_blueprint(agents)

    return app
