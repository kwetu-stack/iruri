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
    negotiations = db.relationship(
        "OfferNegotiation",
        back_populates="property_offer",
        cascade="all, delete-orphan",
        order_by="OfferNegotiation.created_at.desc()",
    )
    reservation = db.relationship(
        "PropertyReservation", back_populates="property_offer", uselist=False
    )

    def __repr__(self):
        return f"<PropertyOffer {self.offer_number}>"


class OfferNegotiation(db.Model):
    """A counter offer exchanged during an offer negotiation."""

    __tablename__ = "offer_negotiations"

    id = db.Column(db.Integer, primary_key=True)
    property_offer_id = db.Column(
        db.Integer,
        db.ForeignKey("property_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    offered_by = db.Column(db.String(50), nullable=False)
    offered_amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    property_offer = db.relationship("PropertyOffer", back_populates="negotiations")

    def __repr__(self):
        return f"<OfferNegotiation {self.id} for offer {self.property_offer_id}>"
