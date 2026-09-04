from datetime import datetime

from app.extensions import db

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column(
        "permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True
    ),
)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    is_system_role = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    permissions = db.relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    users = db.relationship("User", back_populates="role_record")


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    permission_key = db.Column(db.String(150), unique=True, nullable=False, index=True)
    module = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    roles = db.relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )


DEFAULT_ROLES = (
    ("Super Administrator", "Unrestricted platform access.", True),
    ("Administrator", "Manage platform administration.", True),
    ("Manager", "Manage assigned operational work.", True),
    ("Agent", "Manage assigned property and buyer work.", True),
    ("Seller", "Manage owned property listings.", True),
    ("Buyer", "Browse and engage with listings.", True),
    ("Viewer", "Read-only platform access.", True),
)

PERMISSION_GROUPS = {
    "Properties": (
        "property.view",
        "property.create",
        "property.edit",
        "property.delete",
    ),
    "Buyers": ("buyer.view", "buyer.create", "buyer.edit", "buyer.delete"),
    "Sellers": ("seller.view", "seller.create", "seller.edit", "seller.delete"),
    "Transactions": (
        "transaction.view",
        "transaction.create",
        "transaction.edit",
        "transaction.complete",
    ),
    "Administration": (
        "settings.manage",
        "roles.manage",
        "audit.view",
        "backup.manage",
        "email_templates.view",
        "email_templates.manage",
    ),
    "Marketplace": (
        "marketplace.view",
        "marketplace.create",
        "marketplace.edit",
        "marketplace.delete",
    ),
    "Agencies": ("agency.view", "agency.create", "agency.edit", "agency.delete"),
    "Agents": ("agent.view", "agent.create", "agent.edit", "agent.delete"),
    "Developers": (
        "developer.view",
        "developer.create",
        "developer.edit",
        "developer.delete",
    ),
    "Commissions": (
        "commission.view",
        "commission.create",
        "commission.edit",
        "commission.delete",
    ),
    "Viewings": ("viewing.view", "viewing.create", "viewing.edit", "viewing.delete"),
    "Offers": ("offer.view", "offer.create", "offer.edit", "offer.delete"),
    "Reservations": (
        "reservation.view",
        "reservation.create",
        "reservation.edit",
        "reservation.delete",
    ),
    "Sale Agreements": (
        "sale_agreement.view",
        "sale_agreement.create",
        "sale_agreement.edit",
        "sale_agreement.delete",
    ),
    "Dashboard": ("dashboard.view",),
    "Reports": ("reports.executive",),
}


def seed_default_roles_and_permissions():
    from sqlalchemy.exc import OperationalError

    try:
        roles = {role.name: role for role in Role.query.all()}
    except OperationalError:
        db.session.rollback()
        return
    for name, description, is_system_role in DEFAULT_ROLES:
        if name not in roles:
            roles[name] = Role(
                name=name, description=description, is_system_role=is_system_role
            )
            db.session.add(roles[name])

    permissions = {
        permission.permission_key: permission for permission in Permission.query.all()
    }
    for module, keys in PERMISSION_GROUPS.items():
        for key in keys:
            if key not in permissions:
                permissions[key] = Permission(
                    permission_key=key,
                    module=module,
                    description=f"Allow {key.rsplit('.', 1)[-1]} access in {module}.",
                )
                db.session.add(permissions[key])
    db.session.commit()

    from app.auth.models import User

    role_by_name = {role.name.lower(): role for role in Role.query.all()}
    for user in User.query.filter(User.role_id.is_(None)).all():
        role = role_by_name.get((user.role or "").lower())
        if role:
            user.role_id = role.id
    db.session.commit()


def has_permission(user, permission_key):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    role = getattr(user, "role_record", None)
    if role and role.is_active:
        if role.name == "Super Administrator":
            return True
        return any(
            permission.permission_key == permission_key
            for permission in role.permissions
        )
    return (getattr(user, "role", "") or "").lower() in {"admin", "administrator"}
