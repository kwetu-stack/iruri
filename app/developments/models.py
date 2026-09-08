from app.extensions import db


class Development(db.Model):
    __tablename__ = "developments"

    id = db.Column(db.Integer, primary_key=True)
    developer_id = db.Column(
        db.Integer, db.ForeignKey("developers.id"), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    county = db.Column(db.String(100), nullable=False)
    town = db.Column(db.String(100), nullable=False)
    neighbourhood = db.Column(db.String(150))
    property_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Planned")
    completion_date = db.Column(db.Date)
    starting_price = db.Column(db.Numeric(14, 2))
    cover_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    developer = db.relationship(
        "Developer", backref=db.backref("developments", lazy=True)
    )

    def __repr__(self):
        return f"<Development {self.name}>"
