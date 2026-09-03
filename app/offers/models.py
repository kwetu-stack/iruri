from datetime import datetime
from app.extensions import db

OFFER_STATUSES = (
    "Pending",
    "Under Review",
    "Counter Offered",
    "Accepted",
    "Rejected",
    "Withdrawn",
    "Expired",
)


class PropertyOffer(db.Model):
    """A buyer's offer for a property."""

    __tablename__ = "property_offers"

    id = db.Column(db.Integer, primary_key=True)
    offer_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_id = db.Column(
        db.Integer,
        db.ForeignKey("buyers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = db.Column(
        db.Integer,
        db.ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    offered_price = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="KES")
    status = db.Column(db.String(30), nullable=False, default="Pending", index=True)
    buyer_message = db.Column(db.Text)
    seller_response = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    property = db.relationship("Property", back_populates="offers")
    buyer = db.relationship("Buyer", back_populates="offers")
    agent = db.relationship("Agent", back_populates="offers")

    def __repr__(self):
        return f"<PropertyOffer {self.offer_number}>"
