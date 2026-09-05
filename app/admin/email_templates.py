from datetime import datetime

from app.extensions import db

EMAIL_TEMPLATE_CATEGORIES = (
    "Authentication",
    "Marketplace",
    "Buyer Engagement",
    "Transactions",
    "Administration",
    "Notifications",
    "Marketing",
)

EMAIL_TEMPLATE_VARIABLES = (
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


class EmailTemplate(db.Model):
    __tablename__ = "email_templates"
    __table_args__ = (
        db.CheckConstraint(
            "category IN ('Authentication', 'Marketplace', 'Buyer Engagement', "
            "'Transactions', 'Administration', 'Notifications', 'Marketing')",
            name="ck_email_templates_category",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(150), unique=True, nullable=False, index=True)
    template_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    body_text = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_system_template = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


DEFAULT_EMAIL_TEMPLATES = (
    ("welcome_email", "Welcome Email", "Authentication"),
    ("password_reset", "Password Reset", "Authentication"),
    ("email_verification", "Email Verification", "Authentication"),
    ("property_approved", "Property Approved", "Marketplace"),
    ("property_rejected", "Property Rejected", "Marketplace"),
    ("property_sold", "Property Sold", "Marketplace"),
    ("viewing_confirmation", "Viewing Confirmation", "Buyer Engagement"),
    ("offer_submitted", "Offer Submitted", "Buyer Engagement"),
    ("offer_accepted", "Offer Accepted", "Buyer Engagement"),
    ("counter_offer", "Counter Offer", "Buyer Engagement"),
    ("reservation_created", "Reservation Created", "Transactions"),
    ("payment_received", "Payment Received", "Transactions"),
    ("commission_generated", "Commission Generated", "Transactions"),
    ("transaction_completed", "Transaction Completed", "Transactions"),
    ("role_assigned", "Role Assigned", "Administration"),
    ("account_activated", "Account Activated", "Administration"),
    ("account_disabled", "Account Disabled", "Administration"),
)


def seed_default_email_templates():
    """Add missing system templates without overwriting administrator changes."""
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.exc import OperationalError, ProgrammingError

    if not sa_inspect(db.engine).has_table(EmailTemplate.__tablename__):
        return

    try:
        existing_keys = {
            template_key
            for template_key, in db.session.query(EmailTemplate.template_key)
        }
    except (OperationalError, ProgrammingError):
        db.session.rollback()
        return

    for template_key, template_name, category in DEFAULT_EMAIL_TEMPLATES:
        if template_key in existing_keys:
            continue
        db.session.add(
            EmailTemplate(
                template_key=template_key,
                template_name=template_name,
                category=category,
                subject=template_name,
                body_html=f"<p>Hello {{{{full_name}}}},</p><p>{template_name}</p>",
                body_text=f"Hello {{{{full_name}}}},\n\n{template_name}",
                description=f"System template for {template_name.lower()} notifications.",
                is_system_template=True,
            )
        )
    db.session.commit()
