from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """IRURI User Model"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(50), nullable=False, default="Buyer")
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    role_record = db.relationship("Role", back_populates="users")

    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_key):
        from app.admin.roles import has_permission

        return has_permission(self, permission_key)

    def __repr__(self):
        return f"<User {self.email}>"
