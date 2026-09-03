from datetime import datetime

from app.extensions import db

AGREEMENT_STATUSES = (
    "Draft",
    "Pending Signatures",
    "Active",
    "Completed",
    "Cancelled",
)


class SaleAgreement(db.Model):
    """Contract record created from an active property reservation."""

    __tablename__ = "sale_agreements"
    __table_args__ = (
        db.CheckConstraint("agreed_price > 0", name="ck_sale_agreement_price_positive"),
        db.Index(
            "uq_active_sale_agreement_reservation",
            "reservation_id",
            unique=True,
            sqlite_where=db.text("status = 'Active'"),
            postgresql_where=db.text("status = 'Active'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    agreement_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    reservation_id = db.Column(
        db.Integer,
        db.ForeignKey("property_reservations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agreed_price = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="KES")
    agreement_date = db.Column(db.Date, nullable=False)
    completion_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Draft", index=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    reservation = db.relationship(
        "PropertyReservation", back_populates="sale_agreements"
    )
    property = db.relationship("Property", back_populates="sale_agreements")
    buyer = db.relationship("Buyer", back_populates="sale_agreements")
    seller = db.relationship("Seller", back_populates="sale_agreements")

    def __repr__(self):
        return f"<SaleAgreement {self.agreement_number}>"
