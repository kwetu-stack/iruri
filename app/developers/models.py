from datetime import datetime

from app.extensions import db


class Developer(db.Model):
    """Property development company profile."""

    __tablename__ = "developers"

    id = db.Column(db.Integer, primary_key=True)
    developer_number = db.Column(db.String(30), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
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
    specialization = db.Column(db.String(255))
    total_projects = db.Column(db.Integer, default=0, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Developer {self.developer_number}>"
