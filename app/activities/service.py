from datetime import datetime
from uuid import uuid4

from flask_login import current_user

from app.activities.models import ActivityLog
from app.extensions import db


def record_activity(
    activity_type,
    module,
    title,
    description,
    related_record_id=None,
    related_record_type=None,
    commit=True,
):
    if not activity_type or not module or not title:
        raise ValueError("Activity type, module, and title are required")

    authenticated = bool(getattr(current_user, "is_authenticated", False))
    activity = ActivityLog(
        activity_number=f"ACT-{datetime.utcnow().year}-{uuid4().hex[:16].upper()}",
        user_id=current_user.id if authenticated else None,
        activity_type=activity_type,
        module=module,
        title=title,
        description=description,
        related_record_id=related_record_id,
        related_record_type=related_record_type,
    )
    db.session.add(activity)
    if commit:
        db.session.commit()
    return activity
