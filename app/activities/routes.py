from datetime import datetime, timedelta

from flask import abort, render_template, request
from flask_login import current_user, login_required

from app.activities import activities
from app.activities.models import ActivityLog
from app.auth.models import User
from app.extensions import db


def _is_admin():
    role = (getattr(current_user, "role", "") or "").lower()
    role_name = (
        getattr(getattr(current_user, "role_record", None), "name", "") or ""
    ).lower()
    return role in {"admin", "administrator", "super administrator"} or role_name in {
        "administrator",
        "super administrator",
    }


def _visible_query():
    query = ActivityLog.query
    if not _is_admin():
        query = query.filter(ActivityLog.user_id == current_user.id)
    return query


@activities.route("/")
@login_required
def index():
    query = _visible_query()
    user_id = request.args.get("user_id", type=int)
    module = request.args.get("module", "").strip()
    activity_type = request.args.get("activity_type", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search = request.args.get("search", "").strip()

    if _is_admin() and user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    if module:
        query = query.filter(ActivityLog.module == module)
    if activity_type:
        query = query.filter(ActivityLog.activity_type == activity_type)
    for value, end in ((date_from, False), (date_to, True)):
        if value:
            try:
                parsed = datetime.strptime(value, "%Y-%m-%d")
                query = query.filter(
                    ActivityLog.created_at < parsed + timedelta(days=1)
                    if end
                    else ActivityLog.created_at >= parsed
                )
            except ValueError:
                pass
    if search:
        query = query.filter(
            db.or_(
                ActivityLog.activity_number.ilike(f"%{search}%"),
                ActivityLog.description.ilike(f"%{search}%"),
            )
        )

    logs = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).all()
    users = (
        User.query.order_by(User.first_name, User.last_name).all()
        if _is_admin()
        else []
    )
    return render_template(
        "activities/index.html",
        logs=logs,
        users=users,
        user_id=user_id,
        module=module,
        activity_type=activity_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        modules=db.session.query(ActivityLog.module)
        .distinct()
        .order_by(ActivityLog.module)
        .all(),
        activity_types=db.session.query(ActivityLog.activity_type)
        .distinct()
        .order_by(ActivityLog.activity_type)
        .all(),
    )


@activities.route("/<int:log_id>")
@login_required
def detail(log_id):
    log = ActivityLog.query.get_or_404(log_id)
    if not _is_admin() and log.user_id != current_user.id:
        abort(403)
    return render_template("activities/detail.html", log=log)
