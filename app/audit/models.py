from datetime import datetime

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    event_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    username = db.Column(db.String(150), nullable=False, default="System")
    action = db.Column(db.String(50), nullable=False, index=True)
    module = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(100), nullable=True)
    entity_id = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Success", index=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    user = db.relationship("User", backref=db.backref("audit_logs", lazy="dynamic"))
