from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin import admin
from app.admin.models import SystemSetting
from app.admin.roles import PERMISSION_GROUPS, Permission, Role
from app.extensions import db
from app.audit.service import record_audit
from app.notifications.service import administrator_users, notify_users

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
        } and getattr(getattr(current_user, "role_record", None), "name", "") not in {
            "Administrator",
            "Super Administrator",
        }:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def roles_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if (getattr(current_user, "role", "") or "").lower() not in {
            "admin",
            "administrator",
            "super administrator",
        } and not (
            getattr(getattr(current_user, "role_record", None), "name", "")
            in {"Administrator", "Super Administrator"}
        ):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin.route("/roles")
@admin.route("/roles/", strict_slashes=False)
@roles_admin_required
def roles_index():
    roles = Role.query.order_by(Role.name).all()
    return render_template("admin/roles/index.html", roles=roles)


@admin.route("/roles/new", methods=["GET", "POST"])
@roles_admin_required
def role_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Role name is required.", "danger")
        elif Role.query.filter_by(name=name).first():
            flash("A role with that name already exists.", "danger")
        else:
            role = Role(
                name=name, description=request.form.get("description", "").strip()
            )
            db.session.add(role)
            db.session.commit()
            record_audit(
                "Create",
                "Administration",
                f"Role {role.name} created",
                "Role",
                role.id,
            )
            flash("Role created.", "success")
            return redirect(url_for("admin.role_detail", role_id=role.id))
    return render_template("admin/roles/form.html", role=None)


@admin.route("/roles/<int:role_id>")
@roles_admin_required
def role_detail(role_id):
    role = Role.query.get_or_404(role_id)
    grouped_permissions = {
        module: Permission.query.filter(Permission.module == module)
        .order_by(Permission.permission_key)
        .all()
        for module in PERMISSION_GROUPS
    }
    return render_template(
        "admin/roles/detail.html", role=role, grouped_permissions=grouped_permissions
    )


@admin.route("/roles/<int:role_id>/edit", methods=["GET", "POST"])
@roles_admin_required
def role_edit(role_id):
    role = Role.query.get_or_404(role_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duplicate = Role.query.filter(Role.name == name, Role.id != role.id).first()
        if not name or duplicate:
            flash("Role name is required and must be unique.", "danger")
        elif role.name == "Super Administrator" and (
            name != role.name or not request.form.get("is_active")
        ):
            flash(
                "The Super Administrator role cannot be renamed or disabled.", "danger"
            )
        else:
            role.name = name
            role.description = request.form.get("description", "").strip()
            role.is_active = bool(request.form.get("is_active"))
            db.session.commit()
            flash("Role updated.", "success")
            return redirect(url_for("admin.role_detail", role_id=role.id))
    return render_template("admin/roles/form.html", role=role)


@admin.route("/roles/<int:role_id>/permissions", methods=["POST"])
@roles_admin_required
def role_permissions_edit(role_id):
    role = Role.query.get_or_404(role_id)
    keys = set(request.form.getlist("permission_keys"))
    role.permissions = Permission.query.filter(
        Permission.permission_key.in_(keys)
    ).all()
    db.session.commit()
    record_audit(
        "Permission Change",
        "Administration",
        f"Permissions updated for role {role.name}",
        "Role",
        role.id,
    )
    flash("Permissions updated.", "success")
    return redirect(url_for("admin.role_detail", role_id=role.id))


@admin.route("/permissions")
@admin.route("/permissions/", strict_slashes=False)
@roles_admin_required
def permissions_index():
    grouped_permissions = {
        module: Permission.query.filter_by(module=module)
        .order_by(Permission.permission_key)
        .all()
        for module in PERMISSION_GROUPS
    }
    return render_template(
        "admin/roles/permissions.html", grouped_permissions=grouped_permissions
    )


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
            old_value = setting.setting_value
            setting.setting_value = setting.validate_value(
                request.form.get("setting_value", "")
            )
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            flash(f"Invalid value: {error}.", "danger")
        else:
            record_audit(
                "System Setting Change",
                "Administration",
                f"Setting {setting.setting_key} changed from {old_value} to {setting.setting_value}",
                "System Setting",
                setting.id,
            )
            notify_users(
                administrator_users(),
                title="System Setting Updated",
                message=f"The system setting {setting.setting_key} was updated.",
                notification_type="Information",
                related_module="Administration",
                related_record_id=setting.id,
                action_url=url_for("admin.setting_detail", setting_id=setting.id),
            )
            db.session.commit()
            flash("Setting updated.", "success")
            return redirect(url_for("admin.setting_detail", setting_id=setting.id))
    return render_template("admin/settings/edit.html", setting=setting)
