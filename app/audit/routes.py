import csv
from datetime import datetime, timedelta
from io import StringIO

from flask import abort, make_response, render_template, request
from flask_login import current_user

from app.audit import audit
from app.audit.models import AuditLog
from app.extensions import db
from app.utils.permissions import require_permission


def _super_admin():
    role = getattr(getattr(current_user, "role_record", None), "name", "")
    return (
        role == "Super Administrator"
        or (getattr(current_user, "role", "") or "").lower() == "super administrator"
    )


@audit.route("/")
@require_permission("audit.view")
def index():
    query = AuditLog.query
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    user = request.args.get("user", "").strip()
    module = request.args.get("module", "").strip()
    action = request.args.get("action", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()
    if date_from:
        try:
            query = query.filter(
                AuditLog.created_at >= datetime.strptime(date_from, "%Y-%m-%d")
            )
        except ValueError:
            date_from = ""
    if date_to:
        try:
            query = query.filter(
                AuditLog.created_at
                < datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            )
        except ValueError:
            date_to = ""
    if user:
        query = query.filter(AuditLog.username.ilike(f"%{user}%"))
    if module:
        query = query.filter_by(module=module)
    if action:
        query = query.filter_by(action=action)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(
            db.or_(
                AuditLog.username.ilike(f"%{search}%"),
                AuditLog.event_number.ilike(f"%{search}%"),
                AuditLog.description.ilike(f"%{search}%"),
            )
        )
    logs = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).all()
    today = datetime.utcnow().date()
    return render_template(
        "audit/index.html",
        logs=logs,
        date_from=date_from,
        date_to=date_to,
        user=user,
        module=module,
        action=action,
        status=status,
        search=search,
        modules=db.session.query(AuditLog.module)
        .distinct()
        .order_by(AuditLog.module)
        .all(),
        actions=db.session.query(AuditLog.action)
        .distinct()
        .order_by(AuditLog.action)
        .all(),
        stats={
            "total": AuditLog.query.count(),
            "logins": AuditLog.query.filter(
                AuditLog.action == "Login",
                AuditLog.created_at >= datetime.combine(today, datetime.min.time()),
            ).count(),
            "failed": AuditLog.query.filter_by(action="Failed Login").count(),
            "transactions": AuditLog.query.filter_by(module="Transactions").count(),
            "admin": AuditLog.query.filter(
                AuditLog.module == "Administration",
                AuditLog.action.in_(
                    [
                        "Create",
                        "Update",
                        "Permission Change",
                        "Role Assignment",
                        "System Setting Change",
                    ]
                ),
            ).count(),
        },
        can_export=_super_admin(),
    )


@audit.route("/<int:log_id>")
@require_permission("audit.view")
def detail(log_id):
    return render_template("audit/detail.html", log=AuditLog.query.get_or_404(log_id))


@audit.route("/export")
@require_permission("audit.view")
def export():
    if not _super_admin():
        abort(403)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "event_number",
            "created_at",
            "username",
            "module",
            "action",
            "status",
            "description",
        ]
    )
    for log in AuditLog.query.order_by(AuditLog.created_at.desc()).all():
        writer.writerow(
            [
                log.event_number,
                log.created_at.isoformat(),
                log.username,
                log.module,
                log.action,
                log.status,
                log.description,
            ]
        )
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=audit-logs.csv"
    return response
