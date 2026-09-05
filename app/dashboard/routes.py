from datetime import datetime

from flask import render_template

from flask_login import current_user, login_required

from app.dashboard import dashboard
from app.activities.models import ActivityLog
from app.leads.models import Lead


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
    lead_stats = {"new": 0, "today": 0, "follow_up": 0, "closed": 0}
    if current_user.has_permission("lead.view"):
        today = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        lead_stats = {
            "new": Lead.query.filter_by(status="New").count(),
            "today": Lead.query.filter(Lead.created_at >= today).count(),
            "follow_up": Lead.query.filter(
                Lead.status.in_(("New", "Contacted"))
            ).count(),
            "closed": Lead.query.filter_by(status="Closed").count(),
        }
    return render_template(
        "dashboard/index.html",
        recent_activities=recent_activities,
        lead_stats=lead_stats,
    )
