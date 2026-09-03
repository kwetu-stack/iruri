from datetime import datetime
from decimal import Decimal

from app.extensions import db

COMMISSION_TYPES = (
    "Agent Commission",
    "Agency Commission",
    "Platform Commission",
    "Referral Commission",
    "Other",
)
COMMISSION_STATUSES = ("Pending", "Partially Paid", "Paid", "Cancelled")


class PropertyCommission(db.Model):
    __tablename__ = "property_commissions"
    __table_args__ = (
        db.CheckConstraint(
            "commission_rate >= 0 AND commission_rate <= 100",
            name="ck_commission_rate_range",
        ),
        db.CheckConstraint("sale_price > 0", name="ck_commission_sale_price_positive"),
        db.CheckConstraint(
            "commission_amount >= 0", name="ck_commission_amount_nonnegative"
        ),
        db.CheckConstraint(
            "amount_paid >= 0 AND amount_paid <= commission_amount",
            name="ck_commission_paid_range",
        ),
        db.CheckConstraint("balance >= 0", name="ck_commission_balance_nonnegative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    commission_number = db.Column(
        db.String(30), unique=True, nullable=False, index=True
    )
    sale_agreement_id = db.Column(
        db.Integer,
        db.ForeignKey("sale_agreements.id", ondelete="CASCADE"),
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
    agency_id = db.Column(
        db.Integer,
        db.ForeignKey("agencies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commission_type = db.Column(db.String(40), nullable=False)
    commission_rate = db.Column(db.Numeric(precision=7, scale=4), nullable=False)
    sale_price = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    commission_amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    amount_paid = db.Column(
        db.Numeric(precision=18, scale=2), nullable=False, default=Decimal("0.00")
    )
    balance = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    payment_status = db.Column(
        db.String(30), nullable=False, default="Pending", index=True
    )
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_agreement = db.relationship("SaleAgreement", back_populates="commissions")
    property = db.relationship("Property", back_populates="commissions")
    agent = db.relationship("Agent", back_populates="commissions")
    agency = db.relationship("Agency", back_populates="commissions")
    seller = db.relationship("Seller", back_populates="commissions")
    payments = db.relationship(
        "CommissionPayment",
        back_populates="commission",
        cascade="all, delete-orphan",
        order_by="CommissionPayment.payment_date.desc(), CommissionPayment.id.desc()",
    )

    def recalculate(self):
        self.amount_paid = sum(
            (Decimal(payment.amount) for payment in self.payments), Decimal("0.00")
        )
        self.balance = max(
            Decimal("0.00"), Decimal(self.commission_amount) - self.amount_paid
        )
        self.payment_status = (
            "Paid"
            if self.balance == 0
            else "Partially Paid" if self.amount_paid else "Pending"
        )


class CommissionPayment(db.Model):
    __tablename__ = "commission_payments"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_commission_payment_amount_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    commission_id = db.Column(
        db.Integer,
        db.ForeignKey("property_commissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    commission = db.relationship("PropertyCommission", back_populates="payments")
