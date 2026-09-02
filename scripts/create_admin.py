import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.extensions import db
from app.auth.models import User
app = create_app()

with app.app_context():

    admin = User.query.filter_by(email="admin@iruri.co.ke").first()

    if admin:
        print("✓ Super Administrator already exists.")
    else:
        admin = User(
            first_name="IRURI",
            last_name="Administrator",
            email="admin@iruri.co.ke",
            phone="0700000000",
            role="Super Admin",
            is_verified=True,
            is_active=True,
        )

        admin.set_password("Admin@123")

        db.session.add(admin)
        db.session.commit()

        print("✓ Super Administrator created successfully.")