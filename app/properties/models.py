from datetime import datetime

from app.extensions import db

property_amenities = db.Table(
    "property_amenities",
    db.Column(
        "property_id",
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "amenity_id",
        db.Integer,
        db.ForeignKey("amenities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Amenity(db.Model):
    __tablename__ = "amenities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    properties = db.relationship(
        "Property",
        secondary=property_amenities,
        back_populates="amenities",
    )

    def __repr__(self):
        return f"<Amenity {self.name}>"


class Property(db.Model):
    """IRURI Property Model"""

    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)

    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("sellers.id"),
        nullable=False,
    )

    developer_id = db.Column(
        db.Integer,
        db.ForeignKey("developers.id"),
        nullable=True,
    )

    agent_id = db.Column(
        db.Integer,
        db.ForeignKey("agents.id"),
        nullable=True,
    )

    listing_number = db.Column(db.String(30), unique=True, nullable=False)

    title = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text)

    property_type = db.Column(db.String(50), nullable=False)

    listing_type = db.Column(db.String(30), nullable=False)

    price = db.Column(db.Float, nullable=False)

    currency = db.Column(db.String(10), default="KES")

    county = db.Column(db.String(100))

    town = db.Column(db.String(100))

    estate = db.Column(db.String(150))

    address = db.Column(db.String(255))

    bedrooms = db.Column(db.Integer, default=0)

    bathrooms = db.Column(db.Integer, default=0)

    parking = db.Column(db.Integer, default=0)

    floor_area = db.Column(db.Float)

    land_size = db.Column(db.Float)

    status = db.Column(db.String(30), default="Available")

    featured = db.Column(db.Boolean, default=False)

    verified = db.Column(db.Boolean, default=False)

    views = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    images = db.relationship(
        "PropertyImage", backref="property", lazy=True, cascade="all, delete-orphan"
    )

    amenities = db.relationship(
        "Amenity",
        secondary=property_amenities,
        back_populates="properties",
        lazy="selectin",
    )

    seller = db.relationship("Seller", backref="properties")
    developer = db.relationship("Developer", backref="properties")
    agent = db.relationship("Agent", backref="properties")

    def __repr__(self):
        return f"<Property {self.listing_number}>"
