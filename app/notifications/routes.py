from datetime import datetime
from functools import wraps

from flask import abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.notifications import notifications
from app.notifications.models import Notification


def _is_admin():
    role = (getattr(current_user, "role", "") or "").lower()
    role_name = getattr(getattr(current_user, "role_record", None), "name", "")
    return role in {"admin", "administrator", "super administrator"} or role_name in {
        "Administrator",
        "Super Administrator",
    }


def _owned(notification):
    return _is_admin() or notification.recipient_id == current_user.id


@notifications.app_context_processor
def notification_navigation():
    if not current_user.is_authenticated:
        return {"notification_unread_count": 0, "notification_latest": []}
    query = Notification.query.filter_by(recipient_id=current_user.id)
    return {
        "notification_unread_count": query.filter_by(is_read=False).count(),
        "notification_latest": query.order_by(Notification.created_at.desc())
        .limit(10)
        .all(),
    }


@notifications.route("/")
@notifications.route("", strict_slashes=False)
@login_required
def index():
    query = (
        Notification.query
        if _is_admin()
        else Notification.query.filter_by(recipient_id=current_user.id)
    )
    items = query.order_by(Notification.created_at.desc()).all()
    return render_template(
        "notifications/index.html",
        notifications=items,
        total=len(items),
        unread=sum(not item.is_read for item in items),
        read=sum(item.is_read for item in items),
        high=sum(item.priority == "High" for item in items),
        critical=sum(item.priority == "Critical" for item in items),
    )


@notifications.route("/<int:id>")
@login_required
def detail(id):
    notification = Notification.query.get_or_404(id)
    if not _owned(notification):
        abort(403)
    if not notification.is_read:
        notification.mark_read()
        db.session.commit()
    return render_template("notifications/detail.html", notification=notification)


@notifications.route("/<int:id>/read", methods=["POST"])
@login_required
def mark_read(id):
    notification = Notification.query.get_or_404(id)
    if not _owned(notification):
        abort(403)
    notification.mark_read()
    db.session.commit()
    return redirect(url_for("notifications.detail", id=id))


@notifications.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    query = Notification.query.filter_by(is_read=False)
    if not _is_admin():
        query = query.filter_by(recipient_id=current_user.id)
    for notification in query.all():
        notification.mark_read()
    db.session.commit()
    return redirect(url_for("notifications.index"))


@notifications.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    if not _is_admin():
        abort(403)
    notification = Notification.query.get_or_404(id)
    db.session.delete(notification)
    db.session.commit()
    return redirect(url_for("notifications.index"))
