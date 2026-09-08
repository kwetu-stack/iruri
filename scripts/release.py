"""Release-phase task for Railway.

Runs once per deploy, BEFORE the web process (Gunicorn) starts:

    1. Apply Alembic migrations (flask db upgrade).
    2. Verify the required tables now exist (fail loudly if not).
    3. Seed default lookup data (idempotent).

Keep the web process free of schema/data setup. If this script exits
non-zero the deploy is aborted and the previous release keeps serving.

Run with:  python scripts/release.py
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import inspect as sa_inspect

from app import create_app, run_seed
from app.extensions import db
from flask_migrate import upgrade as db_upgrade

# Tables the application needs before it can serve traffic.
REQUIRED_TABLES = (
    "users",
    "roles",
    "permissions",
    "system_settings",
    "email_templates",
    "amenities",
    "features",
    "properties",
)


def main():
    app = create_app()
    with app.app_context():
        print("→ Applying database migrations...")
        db_upgrade()  # upgrades ALL heads

        existing = set(sa_inspect(db.engine).get_table_names())
        missing = [t for t in REQUIRED_TABLES if t not in existing]
        if missing:
            print(f"✗ Required tables missing after migration: {', '.join(missing)}")
            sys.exit(1)
        print(f"✓ Schema verified ({len(REQUIRED_TABLES)} required tables present).")

        print("→ Seeding default lookup data...")
        run_seed(app)
        print("✓ Default lookup data seeded.")


if __name__ == "__main__":
    main()
