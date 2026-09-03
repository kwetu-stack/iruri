from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.hybrid import hybrid_property

from app.extensions import db

AGREEMENT_STATUSES = (
    "Draft",
    "Pending Signatures",
    "Active",
    "Completed",
    "Cancelled",
)

PAYMENT_TYPES = (
    "Reservation Fee",
    "Deposit",
    "Installment",
    "Final Payment",
    "Refund",
    "Other",
)

PAYMENT_METHODS = (
    "Cash",
    "Bank Transfer",
    "Cheque",
    "Mobile Money",
    "Card",
    "Other",
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
    payments = db.relationship(
        "PropertyPayment",
        back_populates="sale_agreement",
        cascade="all, delete-orphan",
        order_by="PropertyPayment.payment_date.desc(), PropertyPayment.id.desc()",
    )
    commissions = db.relationship(
        "PropertyCommission",
        back_populates="sale_agreement",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def total_paid(self):
        return sum(
            (
                -payment.amount if payment.payment_type == "Refund" else payment.amount
                for payment in self.payments
            ),
            Decimal("0.00"),
        )

    @hybrid_property
    def total_received(self):
        return sum(
            (
                payment.amount
                for payment in self.payments
                if payment.payment_type != "Refund"
            ),
            Decimal("0.00"),
        )

    @hybrid_property
    def outstanding_balance(self):
        return max(Decimal("0.00"), Decimal(self.agreed_price) - self.total_paid)

    @hybrid_property
    def percentage_paid(self):
        if not self.agreed_price:
            return Decimal("0.00")
        return min(
            Decimal("100.00"),
            (self.total_paid / Decimal(self.agreed_price) * 100),
        ).quantize(Decimal("0.01"))

    def __repr__(self):
        return f"<SaleAgreement {self.agreement_number}>"


class PropertyPayment(db.Model):
    """A payment or refund recorded against a sale agreement."""

    __tablename__ = "property_payments"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_property_payment_amount_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    sale_agreement_id = db.Column(
        db.Integer,
        db.ForeignKey("sale_agreements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_date = db.Column(db.Date, nullable=False)
    payment_type = db.Column(db.String(30), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    reference_number = db.Column(db.String(100))
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="KES")
    received_by = db.Column(db.String(150))
    notes = db.Column(db.Text)
    receipt_number = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_agreement = db.relationship("SaleAgreement", back_populates="payments")

    def __repr__(self):
        return f"<PropertyPayment {self.payment_number}>"
