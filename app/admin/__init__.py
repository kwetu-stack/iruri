from flask import Blueprint

admin = Blueprint("admin", __name__, url_prefix="/admin")


from app.admin.models import SystemSetting
from app.admin.roles import Permission, Role, seed_default_roles_and_permissions

# Import routes after the blueprint and model are available.
from app.admin import routes

DEFAULT_SETTINGS = (
    {
        "setting_key": "system_name",
        "setting_value": "IRURI Property Marketplace",
        "category": "General",
        "description": "The name displayed for the platform.",
        "data_type": "string",
    },
    {
        "setting_key": "company_name",
        "setting_value": "IRURI",
        "category": "Company",
        "description": "The legal or trading name of the company.",
        "data_type": "string",
    },
    {
        "setting_key": "default_currency",
        "setting_value": "KES",
        "category": "General",
        "description": "The default currency used by the platform.",
        "data_type": "string",
    },
    {
        "setting_key": "time_zone",
        "setting_value": "Africa/Nairobi",
        "category": "General",
        "description": "The platform time zone.",
        "data_type": "string",
    },
    {
        "setting_key": "date_format",
        "setting_value": "%Y-%m-%d",
        "category": "General",
        "description": "The date format used in platform displays.",
        "data_type": "string",
    },
    {
        "setting_key": "allow_public_listings",
        "setting_value": "true",
        "category": "Marketplace",
        "description": "Allow properties to be publicly listed.",
        "data_type": "boolean",
    },
    {
        "setting_key": "require_property_approval",
        "setting_value": "true",
        "category": "Marketplace",
        "description": "Require administrator approval before publishing properties.",
        "data_type": "boolean",
    },
    {
        "setting_key": "default_property_status",
        "setting_value": "Pending",
        "category": "Marketplace",
        "description": "The initial status assigned to new properties.",
        "data_type": "string",
    },
    {
        "setting_key": "reservation_expiry_days",
        "setting_value": "7",
        "category": "Transactions",
        "description": "Number of days before an unpaid reservation expires.",
        "data_type": "integer",
    },
    {
        "setting_key": "default_commission_rate",
        "setting_value": "5.0",
        "category": "Transactions",
        "description": "The default commission rate as a percentage.",
        "data_type": "float",
    },
    {
        "setting_key": "email_notifications_enabled",
        "setting_value": "true",
        "category": "Notifications",
        "description": "Enable platform email notifications.",
        "data_type": "boolean",
    },
    {
        "setting_key": "sms_notifications_enabled",
        "setting_value": "false",
        "category": "Notifications",
        "description": "Enable platform SMS notifications.",
        "data_type": "boolean",
    },
    {
        "setting_key": "session_timeout",
        "setting_value": "3600",
        "category": "Security",
        "description": "Session timeout in seconds.",
        "data_type": "integer",
    },
    {
        "setting_key": "maximum_login_attempts",
        "setting_value": "5",
        "category": "Security",
        "description": "Maximum failed login attempts allowed.",
        "data_type": "integer",
    },
)


def seed_default_settings():
    """Add missing defaults without overwriting administrator changes."""
    from sqlalchemy.exc import OperationalError

    try:
        existing_keys = {
            setting_key
            for setting_key, in SystemSetting.query.with_entities(
                SystemSetting.setting_key
            ).all()
        }
    except OperationalError:
        from app.extensions import db

        db.session.rollback()
        return

    missing = [
        SystemSetting(**setting)
        for setting in DEFAULT_SETTINGS
        if setting["setting_key"] not in existing_keys
    ]
    if missing:
        from app.extensions import db

        db.session.add_all(missing)
        db.session.commit()
