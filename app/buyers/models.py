from datetime import datetime

from app.extensions import db


class Buyer(db.Model):
    """Registered property buyer profile."""

    __tablename__ = "buyers"

    id = db.Column(db.Integer, primary_key=True)
    buyer_number = db.Column(db.String(30), unique=True, nullable=False)
    buyer_type = db.Column(db.String(50), nullable=False)
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
    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    preferred_property_type = db.Column(db.String(100))
    preferred_county = db.Column(db.String(100))
    preferred_town = db.Column(db.String(100))
    financing_method = db.Column(db.String(100))
    profile_photo = db.Column(db.String(255))
    notes = db.Column(db.Text)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Buyer {self.buyer_number}>"
