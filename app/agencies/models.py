from datetime import datetime

from app.extensions import db


class Agency(db.Model):
    """Real estate agency profile."""

    __tablename__ = "agencies"

    id = db.Column(db.Integer, primary_key=True)
    agency_number = db.Column(db.String(30), unique=True, nullable=False)
    agency_name = db.Column(db.String(200), nullable=False)
    registration_number = db.Column(db.String(100))
    license_number = db.Column(db.String(100))
    kra_pin = db.Column(db.String(100))
    phone = db.Column(db.String(30), nullable=False)
    alternative_phone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    website = db.Column(db.String(255))
    county = db.Column(db.String(100))
    town = db.Column(db.String(100))
    address = db.Column(db.String(255))
    postal_address = db.Column(db.String(255))
    description = db.Column(db.Text)
    year_established = db.Column(db.Integer)
    logo = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    commissions = db.relationship("PropertyCommission", back_populates="agency")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Agency {self.agency_number}>"
