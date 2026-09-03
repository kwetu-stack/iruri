from datetime import datetime

from app.extensions import db

NOTIFICATION_TYPES = ("Information", "Success", "Warning", "Error", "Reminder")
PRIORITY_LEVELS = ("Low", "Normal", "High", "Critical")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    notification_number = db.Column(
        db.String(40), unique=True, nullable=False, index=True
    )
    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(30), nullable=False, default="Information")
    priority = db.Column(db.String(20), nullable=False, default="Normal")
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    read_at = db.Column(db.DateTime)
    action_url = db.Column(db.String(500))
    related_module = db.Column(db.String(80))
    related_record_id = db.Column(db.Integer)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    recipient = db.relationship("User", back_populates="notifications")

    __table_args__ = (
        db.CheckConstraint(
            "notification_type IN ('Information', 'Success', 'Warning', 'Error', 'Reminder')",
            name="ck_notifications_type",
        ),
        db.CheckConstraint(
            "priority IN ('Low', 'Normal', 'High', 'Critical')",
            name="ck_notifications_priority",
        ),
    )

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
