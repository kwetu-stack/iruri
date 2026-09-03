from datetime import datetime

from app.extensions import db

TRANSACTION_STATUSES = ("Pending Completion", "Completed", "Cancelled")


class PropertyTransaction(db.Model):
    __tablename__ = "property_transactions"
    __table_args__ = (
        db.CheckConstraint(
            "final_sale_price > 0", name="ck_transaction_sale_price_positive"
        ),
        db.Index(
            "uq_completed_transaction_property",
            "property_id",
            unique=True,
            sqlite_where=db.text("transaction_status = 'Completed'"),
            postgresql_where=db.text("transaction_status = 'Completed'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    transaction_number = db.Column(
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
    completion_date = db.Column(db.Date, nullable=False)
    transfer_date = db.Column(db.Date, nullable=True)
    final_sale_price = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="KES")
    transaction_status = db.Column(
        db.String(30), nullable=False, default="Pending Completion", index=True
    )
    completed_by = db.Column(db.String(150), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_agreement = db.relationship("SaleAgreement", back_populates="transactions")
    property = db.relationship("Property", back_populates="transactions")
    buyer = db.relationship("Buyer", back_populates="transactions")
    seller = db.relationship("Seller", back_populates="transactions")

    def __repr__(self):
        return f"<PropertyTransaction {self.transaction_number}>"
