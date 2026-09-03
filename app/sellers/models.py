from datetime import datetime

from app.extensions import db


class Seller(db.Model):
    """Property seller profile."""

    __tablename__ = "sellers"

    id = db.Column(db.Integer, primary_key=True)
    seller_number = db.Column(db.String(30), unique=True, nullable=False)
    seller_type = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(200))
    company_name = db.Column(db.String(200))
    national_id = db.Column(db.String(100))
    passport_number = db.Column(db.String(100))
    kra_pin = db.Column(db.String(100))
    phone = db.Column(db.String(30), nullable=False)
    alternative_phone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    county = db.Column(db.String(100))
    town = db.Column(db.String(100))
    address = db.Column(db.String(255))
    postal_address = db.Column(db.String(255))
    profile_photo = db.Column(db.String(255))
    description = db.Column(db.Text)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sale_agreements = db.relationship(
        "SaleAgreement",
        back_populates="seller",
        cascade="all, delete-orphan",
        order_by="SaleAgreement.created_at.desc()",
    )
    commissions = db.relationship(
        "PropertyCommission", back_populates="seller", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Seller {self.seller_number}>"
