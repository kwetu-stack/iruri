from flask import Blueprint

auth = Blueprint("auth", __name__, url_prefix="/auth")

from app.auth import routes

DEFAULT_ADMIN_EMAIL = "admin@iruri.com"
DEFAULT_ADMIN_PASSWORD = "Admin@123"


def seed_admin_user():
    """Create the default Administrator account. Idempotent — skips if it already exists."""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.exc import OperationalError, ProgrammingError

    from app.admin.roles import Role
    from app.auth.models import User
    from app.extensions import db

    inspector = sa_inspect(db.engine)
    if not (
        inspector.has_table(User.__tablename__)
        and inspector.has_table(Role.__tablename__)
    ):
        return

    try:
        if User.query.filter_by(email=DEFAULT_ADMIN_EMAIL).first() is not None:
            return
        role = Role.query.filter_by(name="Administrator").first()
    except (OperationalError, ProgrammingError):
        db.session.rollback()
        return

    admin = User(
        first_name="Administrator",
        last_name="",
        email=DEFAULT_ADMIN_EMAIL,
        role="Administrator",
        role_id=role.id if role else None,
        is_verified=True,
        is_active=True,
    )
    admin.set_password(DEFAULT_ADMIN_PASSWORD)
    db.session.add(admin)
    db.session.commit()
