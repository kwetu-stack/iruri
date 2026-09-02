from flask import Flask

from config import Config
from app.extensions import db, migrate, login_manager
from app.auth import auth

import app.models


def create_app():
    """Application Factory."""

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @app.route("/")
    def home():
        return "<h1>Welcome to IRURI™</h1>"

    app.register_blueprint(auth)

    return app