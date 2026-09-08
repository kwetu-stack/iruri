import hashlib
import mimetypes
import os
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.media.models import MediaAsset

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"}
DEFAULT_LIMITS = {
    "image": 10 * 1024 * 1024,
    "video": 500 * 1024 * 1024,
    "document": 50 * 1024 * 1024,
}


class MediaService:
    @classmethod
    def migrate_legacy_uploads(cls):
        legacy_root = Path(current_app.static_folder) / "uploads"
        migrated = 0
        if not legacy_root.is_dir():
            return migrated
        for source in legacy_root.rglob("*"):
            if not source.is_file():
                continue
            module = source.parent.name
            relative = source.relative_to(legacy_root).as_posix()
            if MediaAsset.query.filter_by(storage_path=relative).first():
                continue
            payload = source.read_bytes()
            extension = source.suffix.lstrip(".").lower()
            mime_type = (
                mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            )
            target = cls.storage_root() / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            asset = MediaAsset(
                filename=f"{uuid.uuid4().hex}_{source.name}",
                original_filename=source.name,
                file_extension=extension,
                mime_type=mime_type,
                file_size=len(payload),
                storage_path=relative,
                public_url=f"/media/legacy/{relative}",
                checksum=hashlib.sha256(payload).hexdigest(),
                module=module,
            )
            db.session.add(asset)
            migrated += 1
        db.session.commit()
        return migrated

    @staticmethod
    def find(module, record_id, filename):
        return MediaAsset.query.filter_by(
            module=module, record_id=record_id, filename=filename, status="active"
        ).first()

    @staticmethod
    def storage_root():
        root = current_app.config["MEDIA_STORAGE_ROOT"]
        path = Path(root)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def classify(extension, mime_type):
        extension = extension.lower()
        if mime_type.startswith("image/") or extension in IMAGE_EXTENSIONS:
            return "image"
        if mime_type.startswith("video/") or extension in VIDEO_EXTENSIONS:
            return "video"
        return "document"

    @classmethod
    def validate(cls, uploaded_file, allowed_extensions=None, max_size=None):
        original = secure_filename(uploaded_file.filename or "")
        if not original or "." not in original:
            raise ValueError("A file with an extension is required.")
        extension = original.rsplit(".", 1)[1].lower()
        mime_type = (
            uploaded_file.mimetype
            or mimetypes.guess_type(original)[0]
            or "application/octet-stream"
        )
        category = cls.classify(extension, mime_type)
        allowed = set(
            allowed_extensions
            or (IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | DOCUMENT_EXTENSIONS)
        )
        if extension not in allowed:
            raise ValueError(f"The .{extension} file type is not supported.")
        uploaded_file.stream.seek(0, os.SEEK_END)
        size = uploaded_file.stream.tell()
        uploaded_file.stream.seek(0)
        if size > (max_size or DEFAULT_LIMITS[category]):
            raise ValueError("The uploaded file exceeds the allowed size.")
        return original, extension, mime_type, category, size

    @classmethod
    def upload(
        cls,
        uploaded_file,
        module,
        record_id=None,
        uploaded_by=None,
        is_cover=False,
        display_order=0,
        allowed_extensions=None,
        max_size=None,
    ):
        original, extension, mime_type, category, size = cls.validate(
            uploaded_file, allowed_extensions, max_size
        )
        checksum = hashlib.sha256()
        payload = uploaded_file.stream.read()
        uploaded_file.stream.seek(0)
        checksum.update(payload)
        filename = f"{uuid.uuid4().hex}.{extension}"
        relative_path = Path(module) / filename
        target = cls.storage_root() / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(target)
        thumbnail_path = None
        width = None
        height = None
        if category == "image":
            try:
                from PIL import Image

                with Image.open(target) as image:
                    width, height = image.size
                    thumbnail = image.copy()
                    thumbnail.thumbnail((640, 640))
                    thumbnail_path = (Path(module) / "thumbnails" / filename).as_posix()
                    thumbnail_target = cls.storage_root() / thumbnail_path
                    thumbnail_target.parent.mkdir(parents=True, exist_ok=True)
                    thumbnail.save(thumbnail_target, format=image.format or "JPEG")
            except (ImportError, OSError):
                pass
        asset = MediaAsset(
            filename=filename,
            original_filename=original,
            file_extension=extension,
            mime_type=mime_type,
            file_size=size,
            storage_path=relative_path.as_posix(),
            thumbnail_path=thumbnail_path,
            public_url="/media/0",
            checksum=checksum.hexdigest(),
            uploaded_by=uploaded_by,
            module=module,
            record_id=record_id,
            is_cover=is_cover,
            display_order=display_order,
        )
        db.session.add(asset)
        db.session.flush()
        asset.public_url = f"/media/{asset.id}"
        return asset

    @classmethod
    def replace(cls, asset, uploaded_file, **kwargs):
        for key in ("module", "record_id", "uploaded_by", "is_cover", "display_order"):
            kwargs.pop(key, None)
        new_asset = cls.upload(
            uploaded_file,
            module=asset.module,
            record_id=asset.record_id,
            uploaded_by=asset.uploaded_by,
            is_cover=asset.is_cover,
            display_order=asset.display_order,
            **kwargs,
        )
        cls.delete(asset, commit=False)
        return new_asset

    @classmethod
    def delete(cls, asset, commit=True):
        path = cls.storage_root() / asset.storage_path
        if path.is_file():
            path.unlink()
        if asset.thumbnail_path:
            thumbnail = cls.storage_root() / asset.thumbnail_path
            if thumbnail.is_file():
                thumbnail.unlink()
        asset.status = "deleted"
        if commit:
            db.session.commit()

    @classmethod
    def exists(cls, asset):
        return (cls.storage_root() / asset.storage_path).is_file()

    @classmethod
    def url_for_legacy(cls, path):
        if not path:
            return None
        return f"/media/legacy/{path}"
