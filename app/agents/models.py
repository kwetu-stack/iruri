from datetime import datetime

from app.extensions import db


class Agent(db.Model):
    """Real estate agent profile."""

    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)
    agent_number = db.Column(db.String(30), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(30))
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(255))
    national_id = db.Column(db.String(100))
    license_number = db.Column(db.String(100))
    kra_pin = db.Column(db.String(100))
    county = db.Column(db.String(100))
    town = db.Column(db.String(100))
    address = db.Column(db.String(255))
    bio = db.Column(db.Text)
    years_experience = db.Column(db.Integer)
    commission_rate = db.Column(db.Float)
    profile_photo = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Agent {self.agent_number}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
