from flask import render_template

from flask_login import current_user, login_required

from app.dashboard import dashboard
from app.activities.models import ActivityLog


def _is_admin():
    role = (getattr(current_user, "role", "") or "").lower()
    role_name = (
        getattr(getattr(current_user, "role_record", None), "name", "") or ""
    ).lower()
    return role in {"admin", "administrator", "super administrator"} or role_name in {
        "administrator",
        "super administrator",
    }


@dashboard.route("/")
@login_required
def index():
    query = ActivityLog.query
    if not _is_admin():
        query = query.filter_by(user_id=current_user.id)
    recent_activities = (
        query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(10)
        .all()
    )
    return render_template("dashboard/index.html", recent_activities=recent_activities)
