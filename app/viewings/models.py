from datetime import datetime

from app.extensions import db

VIEWING_STATUSES = ("Pending", "Confirmed", "Completed", "Cancelled", "No Show")


class ViewingRequest(db.Model):
    """A buyer's requested appointment to view a property."""

    __tablename__ = "viewing_requests"

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    buyer_id = db.Column(
        db.Integer,
        db.ForeignKey("buyers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
    requested_date = db.Column(db.Date, nullable=False)
    requested_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pending", index=True)
    message = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    buyer = db.relationship("Buyer", back_populates="viewing_requests")
    property = db.relationship("Property", back_populates="viewing_requests")
    agent = db.relationship("Agent", backref="viewing_requests")

    def __repr__(self):
        return f"<ViewingRequest {self.request_number}>"
