from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin import admin
from app.admin.email_templates import EMAIL_TEMPLATE_CATEGORIES, EmailTemplate
from app.admin.models import SystemSetting
from app.admin.roles import PERMISSION_GROUPS, Permission, Role
from app.extensions import db
from app.audit.service import record_audit
from app.activities.service import record_activity
from app.notifications.service import administrator_users, notify_users
from app.utils.permissions import require_permission
import re

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
    record_activity(
        "Role Assigned",
        "Administration",
        "Role Assigned",
        f"Permissions assigned to role {role.name}",
        role.id,
        "Role",
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


def _template_form_values(template=None):
    return {
        "template_key": request.form.get(
            "template_key", template.template_key if template else ""
        ).strip(),
        "template_name": request.form.get(
            "template_name", template.template_name if template else ""
        ).strip(),
        "category": request.form.get(
            "category", template.category if template else ""
        ).strip(),
        "subject": request.form.get(
            "subject", template.subject if template else ""
        ).strip(),
        "body_html": request.form.get(
            "body_html", template.body_html if template else ""
        ),
        "body_text": request.form.get(
            "body_text", template.body_text if template else ""
        ),
        "description": request.form.get(
            "description", template.description if template else ""
        ).strip(),
        "is_active": bool(request.form.get("is_active")),
    }


def _validate_template(values, template=None):
    errors = []
    if not values["template_key"] or not values["template_name"]:
        errors.append("Template key and name are required.")
    if values["category"] not in EMAIL_TEMPLATE_CATEGORIES:
        errors.append("Choose a valid category.")
    if not values["subject"]:
        errors.append("Subject is required.")
    if not values["body_html"].strip():
        errors.append("HTML body is required.")
    duplicate = EmailTemplate.query.filter_by(
        template_key=values["template_key"]
    ).first()
    if duplicate and (template is None or duplicate.id != template.id):
        errors.append("A template with that key already exists.")
    return errors


@admin.route("/email-templates")
@admin.route("/email-templates/", strict_slashes=False)
@require_permission("email_templates.view")
def email_templates_index():
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()
    query = EmailTemplate.query
    if category in EMAIL_TEMPLATE_CATEGORIES:
        query = query.filter_by(category=category)
    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)
    elif status == "system":
        query = query.filter_by(is_system_template=True)
    if search:
        query = query.filter(
            db.or_(
                EmailTemplate.template_name.ilike(f"%{search}%"),
                EmailTemplate.template_key.ilike(f"%{search}%"),
                EmailTemplate.subject.ilike(f"%{search}%"),
            )
        )
    return render_template(
        "admin/email_templates/index.html",
        templates=query.order_by(
            EmailTemplate.category, EmailTemplate.template_name
        ).all(),
        categories=EMAIL_TEMPLATE_CATEGORIES,
        selected_category=category,
        status=status,
        search=search,
    )


@admin.route("/email-templates/new", methods=["GET", "POST"])
@require_permission("email_templates.manage")
def email_template_create():
    values = _template_form_values()
    if request.method == "POST":
        errors = _validate_template(values)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            template = EmailTemplate(**values, is_system_template=False)
            db.session.add(template)
            db.session.commit()
            flash("Email template created.", "success")
            return redirect(
                url_for("admin.email_template_detail", template_id=template.id)
            )
    return render_template(
        "admin/email_templates/form.html",
        template=None,
        values=values,
        categories=EMAIL_TEMPLATE_CATEGORIES,
    )


@admin.route("/email-templates/<int:template_id>")
@require_permission("email_templates.view")
def email_template_detail(template_id):
    return render_template(
        "admin/email_templates/detail.html",
        template=EmailTemplate.query.get_or_404(template_id),
    )


@admin.route("/email-templates/<int:template_id>/edit", methods=["GET", "POST"])
@require_permission("email_templates.manage")
def email_template_edit(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    values = _template_form_values(template)
    if request.method == "POST":
        errors = _validate_template(values, template)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            for field, value in values.items():
                setattr(template, field, value)
            db.session.commit()
            flash("Email template updated.", "success")
            return redirect(
                url_for("admin.email_template_detail", template_id=template.id)
            )
    return render_template(
        "admin/email_templates/form.html",
        template=template,
        values=values,
        categories=EMAIL_TEMPLATE_CATEGORIES,
    )


@admin.route("/email-templates/<int:template_id>/duplicate", methods=["POST"])
@require_permission("email_templates.manage")
def email_template_duplicate(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    base_key = f"{template.template_key}_copy"
    key = base_key
    suffix = 2
    while EmailTemplate.query.filter_by(template_key=key).first():
        key = f"{base_key}_{suffix}"
        suffix += 1
    duplicate = EmailTemplate(
        template_key=key,
        template_name=f"{template.template_name} Copy",
        category=template.category,
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        description=template.description,
        is_active=template.is_active,
        is_system_template=False,
    )
    db.session.add(duplicate)
    db.session.commit()
    flash("Email template duplicated.", "success")
    return redirect(url_for("admin.email_template_edit", template_id=duplicate.id))


@admin.route("/email-templates/<int:template_id>/toggle", methods=["POST"])
@require_permission("email_templates.manage")
def email_template_toggle(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    template.is_active = not template.is_active
    db.session.commit()
    flash("Email template status updated.", "success")
    return redirect(url_for("admin.email_templates_index"))


@admin.route("/email-templates/<int:template_id>/delete", methods=["POST"])
@require_permission("email_templates.manage")
def email_template_delete(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    if template.is_system_template:
        abort(403)
    db.session.delete(template)
    db.session.commit()
    flash("Email template deleted.", "success")
    return redirect(url_for("admin.email_templates_index"))


@admin.route("/email-templates/<int:template_id>/preview")
@require_permission("email_templates.view")
def email_template_preview(template_id):
    template = EmailTemplate.query.get_or_404(template_id)
    samples = {
        variable: variable.replace("_", " ").title()
        for variable in (
            "first_name",
            "last_name",
            "full_name",
            "property_name",
            "property_reference",
            "transaction_number",
            "reservation_number",
            "offer_number",
            "payment_amount",
            "company_name",
            "current_date",
        )
    }

    def replace_variables(value):
        return re.sub(
            r"{{\\s*([a-zA-Z_][a-zA-Z0-9_]*)\\s*}}",
            lambda match: samples.get(match.group(1), match.group(0)),
            value or "",
        )

    return render_template(
        "admin/email_templates/preview.html",
        template=template,
        subject=replace_variables(template.subject),
        body_html=replace_variables(template.body_html),
        body_text=replace_variables(template.body_text),
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
            record_activity(
                "Settings Updated",
                "Administration",
                "Settings Updated",
                f"Setting {setting.setting_key} updated",
                setting.id,
                "System Setting",
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
