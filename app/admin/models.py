from datetime import datetime

from app.extensions import db


class SystemSetting(db.Model):
    __tablename__ = "system_settings"
    __table_args__ = (
        db.CheckConstraint(
            "category IN ('General', 'Company', 'Marketplace', 'Transactions', "
            "'Notifications', 'Security', 'Email', 'Appearance')",
            name="ck_system_settings_category",
        ),
        db.CheckConstraint(
            "data_type IN ('string', 'integer', 'float', 'boolean', 'json')",
            name="ck_system_settings_data_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(150), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.String(20), nullable=False, default="string")
    is_editable = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def typed_value(self):
        """Return the stored value converted according to its declared type."""
        if self.data_type == "boolean":
            return self.setting_value.lower() == "true"
        if self.data_type == "integer":
            return int(self.setting_value)
        if self.data_type == "float":
            return float(self.setting_value)
        if self.data_type == "json":
            import json

            return json.loads(self.setting_value)
        return self.setting_value

    def validate_value(self, value):
        """Validate a form value and return its canonical stored representation."""
        value = value.strip()
        if self.data_type == "boolean":
            normalized = value.lower()
            if normalized not in {"true", "false"}:
                raise ValueError("must be true or false")
            return normalized
        if self.data_type == "integer":
            int(value)
            return value
        if self.data_type == "float":
            float(value)
            return value
        if self.data_type == "json":
            import json

            json.loads(value)
            return value
        return value
