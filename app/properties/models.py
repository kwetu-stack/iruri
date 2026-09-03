from datetime import datetime

from app.extensions import db


class SavedProperty(db.Model):
    """A property saved by a buyer."""

    __tablename__ = "saved_properties"
    __table_args__ = (
        db.UniqueConstraint(
            "buyer_id", "property_id", name="uq_saved_property_buyer_property"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(
        db.Integer,
        db.ForeignKey("buyers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    saved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    buyer = db.relationship("Buyer", back_populates="saved_properties")
    property = db.relationship("Property", back_populates="saved_properties")


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

property_features = db.Table(
    "property_features",
    db.Column(
        "property_id",
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "feature_id",
        db.Integer,
        db.ForeignKey("features.id", ondelete="CASCADE"),
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


class PropertyFeature(db.Model):
    __tablename__ = "features"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    properties = db.relationship(
        "Property",
        secondary=property_features,
        back_populates="features",
    )

    def __repr__(self):
        return f"<PropertyFeature {self.name}>"


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

    county = db.Column(db.String(100), index=True)

    town = db.Column(db.String(100), index=True)

    estate = db.Column(db.String(150), index=True)

    neighbourhood = db.Column(db.String(150), index=True)

    landmark = db.Column(db.String(255))

    postal_code = db.Column(db.String(20))

    latitude = db.Column(db.Float)

    longitude = db.Column(db.Float)

    google_map_url = db.Column(db.String(500))

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

    floor_plans = db.relationship(
        "PropertyFloorPlan",
        back_populates="property",
        lazy=True,
        cascade="all, delete-orphan",
    )

    documents = db.relationship(
        "PropertyDocument",
        back_populates="property",
        lazy=True,
        cascade="all, delete-orphan",
    )

    videos = db.relationship(
        "PropertyVideo",
        back_populates="property",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="PropertyVideo.display_order.asc()",
    )

    amenities = db.relationship(
        "Amenity",
        secondary=property_amenities,
        back_populates="properties",
        lazy="selectin",
    )

    features = db.relationship(
        "PropertyFeature",
        secondary=property_features,
        back_populates="properties",
        lazy="selectin",
    )

    saved_properties = db.relationship(
        "SavedProperty",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="SavedProperty.saved_at.desc()",
    )

    viewing_requests = db.relationship(
        "ViewingRequest",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="ViewingRequest.requested_date.asc()",
    )

    offers = db.relationship(
        "PropertyOffer",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="PropertyOffer.submitted_at.desc()",
    )

    reservations = db.relationship(
        "PropertyReservation",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="PropertyReservation.reservation_date.desc()",
    )

    sale_agreements = db.relationship(
        "SaleAgreement",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="SaleAgreement.created_at.desc()",
    )
    commissions = db.relationship(
        "PropertyCommission", back_populates="property", cascade="all, delete-orphan"
    )
    transactions = db.relationship(
        "PropertyTransaction", back_populates="property", cascade="all, delete-orphan"
    )

    seller = db.relationship("Seller", backref="properties")
    developer = db.relationship("Developer", backref="properties")
    agent = db.relationship("Agent", backref="properties")

    def __repr__(self):
        return f"<Property {self.listing_number}>"


class PropertyFloorPlan(db.Model):
    """A floor plan uploaded for a property listing."""

    __tablename__ = "property_floor_plans"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    floor_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_extension = db.Column(db.String(20), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    property = db.relationship("Property", back_populates="floor_plans")


class PropertyDocument(db.Model):
    """Supporting document uploaded for a property."""

    __tablename__ = "property_documents"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type = db.Column(db.String(100), nullable=False)
    document_name = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_extension = db.Column(db.String(10), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    property = db.relationship("Property", back_populates="documents")


class PropertyVideo(db.Model):
    """An uploaded or externally hosted video for a property listing."""

    __tablename__ = "property_videos"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    video_type = db.Column(db.String(20), nullable=False)
    file_name = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    external_url = db.Column(db.String(500), nullable=True)
    thumbnail = db.Column(db.String(500), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    property = db.relationship("Property", back_populates="videos")
