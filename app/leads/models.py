from datetime import datetime

from app.extensions import db

LEAD_STATUSES = (
    "New",
    "Contacted",
    "Viewing Scheduled",
    "Negotiating",
    "Closed",
    "Lost",
)
PREFERRED_CONTACT_METHODS = ("Email", "Phone", "WhatsApp")
LEAD_SOURCES = ("Request Viewing", "Contact Agent", "Send Enquiry", "Website")


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = db.Column(
        db.Integer,
        db.ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False)
    preferred_contact = db.Column(db.String(30), nullable=False, default="Email")
    message = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Numeric(18, 2), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="New", index=True)
    source = db.Column(db.String(40), nullable=False, default="Website")
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    property = db.relationship("Property", backref=db.backref("leads", lazy=True))
    agent = db.relationship("Agent", backref=db.backref("leads", lazy=True))

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('New', 'Contacted', 'Viewing Scheduled', 'Negotiating', 'Closed', 'Lost')",
            name="ck_leads_status",
        ),
        db.CheckConstraint(
            "preferred_contact IN ('Email', 'Phone', 'WhatsApp')",
            name="ck_leads_preferred_contact",
        ),
    )

    def __repr__(self):
        return f"<Lead {self.reference_number}>"
