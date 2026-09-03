from app.auth.models import User
from app.extensions import db
from app.notifications.models import Notification, NOTIFICATION_TYPES, PRIORITY_LEVELS


def user_for_email(email):
    if not email:
        return None
    return User.query.filter(db.func.lower(User.email) == email.strip().lower()).first()


def create_notification(
    recipient,
    title,
    message,
    notification_type="Information",
    priority="Normal",
    action_url=None,
    related_module=None,
    related_record_id=None,
):
    """Create an in-app notification; delivery adapters can be added here later."""
    recipient_id = getattr(recipient, "id", recipient)
    if not recipient_id or not title or not message:
        raise ValueError("A recipient, title, and message are required.")
    if notification_type not in NOTIFICATION_TYPES:
        raise ValueError("Invalid notification type.")
    if priority not in PRIORITY_LEVELS:
        raise ValueError("Invalid notification priority.")
    notification = Notification(
        notification_number="TEMP",
        recipient_id=recipient_id,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        related_module=related_module,
        related_record_id=related_record_id,
    )
    db.session.add(notification)
    db.session.flush()
    notification.notification_number = f"NTF-{notification.id:010d}"
    return notification


def notify_profile(profile, **values):
    user = user_for_email(getattr(profile, "email", None))
    return create_notification(user, **values) if user else None


def notify_users(users, **values):
    created = []
    for user in users:
        notification = create_notification(user, **values)
        created.append(notification)
    return created


def administrator_users():
    return [
        user
        for user in User.query.all()
        if (user.role or "").lower()
        in {"admin", "administrator", "super administrator"}
        or getattr(getattr(user, "role_record", None), "name", "")
        in {"Administrator", "Super Administrator"}
    ]
