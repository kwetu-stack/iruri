from datetime import datetime

from app.extensions import db

RESERVATION_STATUSES = ("Pending", "Active", "Expired", "Cancelled", "Completed")


class PropertyReservation(db.Model):
    """A reservation securing a property after an accepted offer."""

    __tablename__ = "property_reservations"
    __table_args__ = (
        db.CheckConstraint(
            "reservation_fee >= 0", name="ck_reservation_fee_non_negative"
        ),
        db.Index(
            "uq_active_reservation_property",
            "property_id",
            unique=True,
            sqlite_where=db.text("status = 'Active'"),
            postgresql_where=db.text("status = 'Active'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    reservation_number = db.Column(
        db.String(30), unique=True, nullable=False, index=True
    )
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
    property_offer_id = db.Column(
        db.Integer,
        db.ForeignKey("property_offers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    reserved_by = db.Column(db.String(100), nullable=False)
    reservation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=False)
    reservation_fee = db.Column(
        db.Numeric(precision=18, scale=2), nullable=False, default=0
    )
    currency = db.Column(db.String(10), nullable=False, default="KES")
    status = db.Column(db.String(20), nullable=False, default="Pending", index=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    property = db.relationship("Property", back_populates="reservations")
    buyer = db.relationship("Buyer", back_populates="reservations")
    property_offer = db.relationship("PropertyOffer", back_populates="reservation")

    def __repr__(self):
        return f"<PropertyReservation {self.reservation_number}>"
