from datetime import datetime

from app.extensions import db


class MediaAsset(db.Model):
    __tablename__ = "media_assets"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_extension = db.Column(db.String(20), nullable=False)
    mime_type = db.Column(db.String(150), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False, default=0)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    duration = db.Column(db.Numeric(12, 3))
    storage_path = db.Column(db.String(500), nullable=False)
    thumbnail_path = db.Column(db.String(500))
    public_url = db.Column(db.String(500), nullable=False)
    checksum = db.Column(db.String(64), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    module = db.Column(db.String(80), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=True, index=True)
    is_cover = db.Column(db.Boolean, nullable=False, default=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="active", index=True)

    uploader = db.relationship("User", foreign_keys=[uploaded_by])

    @property
    def media_type(self):
        if self.mime_type.startswith("image/"):
            return "Image"
        if self.mime_type.startswith("video/"):
            return "Video"
        if self.mime_type == "application/pdf":
            return "PDF"
        return "Document"

    @property
    def thumbnail_url(self):
        return (
            self.public_url
            if not self.thumbnail_path
            else self.public_url.rsplit("/", 1)[0] + "/thumbnail/" + str(self.id)
        )
