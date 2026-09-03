from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin import admin
from app.admin.models import SystemSetting
from app.extensions import db

CATEGORIES = (
    "General",
    "Company",
    "Marketplace",
    "Transactions",
    "Notifications",
    "Security",
    "Email",
    "Appearance",
)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if (getattr(current_user, "role", "") or "").lower() not in {
            "admin",
            "administrator",
        }:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin.route("/settings")
@admin.route("/settings/", strict_slashes=False)
@admin_required
def settings_index():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()
    query = SystemSetting.query
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(SystemSetting.setting_key.ilike(f"%{search}%"))
    settings = query.order_by(SystemSetting.category, SystemSetting.setting_key).all()
    return render_template(
        "admin/settings/index.html",
        settings=settings,
        categories=CATEGORIES,
        selected_category=category,
        search=search,
    )


@admin.route("/settings/<int:setting_id>")
@admin_required
def setting_detail(setting_id):
    setting = SystemSetting.query.get_or_404(setting_id)
    return render_template("admin/settings/detail.html", setting=setting)


@admin.route("/settings/<int:setting_id>/edit", methods=["GET", "POST"])
@admin_required
def setting_edit(setting_id):
    setting = SystemSetting.query.get_or_404(setting_id)
    if not setting.is_editable:
        abort(403)
    if request.method == "POST":
        try:
            setting.setting_value = setting.validate_value(
                request.form.get("setting_value", "")
            )
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(f"Invalid value: {error}.", "danger")
        else:
            flash("Setting updated.", "success")
            return redirect(url_for("admin.setting_detail", setting_id=setting.id))
    return render_template("admin/settings/edit.html", setting=setting)
