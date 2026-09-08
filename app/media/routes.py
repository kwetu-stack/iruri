from pathlib import Path

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user
from sqlalchemy import or_

from app.media import media
from app.media.models import MediaAsset
from app.media.service import MediaService
from app.extensions import db
from app.utils.permissions import require_permission
from functools import wraps
from flask import abort
from app.admin.roles import has_permission


def media_permission(permission_key):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return require_permission(permission_key)(view)(*args, **kwargs)
            role = (getattr(current_user, "role", "") or "").lower()
            role_record = (
                getattr(getattr(current_user, "role_record", None), "name", "") or ""
            ).lower()
            administrator = role in {
                "admin",
                "administrator",
                "super administrator",
            } or role_record in {"administrator", "super administrator"}
            if not administrator and not has_permission(current_user, permission_key):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


@media.get("/<int:asset_id>")
def serve(asset_id):
    asset = MediaAsset.query.filter_by(id=asset_id, status="active").first_or_404()
    path = MediaService.storage_root() / asset.storage_path
    if not path.is_file():
        abort(404)
    return send_file(
        path, mimetype=asset.mime_type, conditional=True, etag=asset.checksum
    )


@media.get("/<int:asset_id>/thumbnail")
def thumbnail(asset_id):
    asset = MediaAsset.query.filter_by(id=asset_id, status="active").first_or_404()
    path = MediaService.storage_root() / (asset.thumbnail_path or asset.storage_path)
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype=asset.mime_type, conditional=True)


@media.get("/legacy/<path:path>")
def legacy(path):
    root = Path(current_app.config["MEDIA_STORAGE_ROOT"])
    requested = (root / path).resolve()
    if root.resolve() in requested.parents and requested.is_file():
        return send_file(requested, conditional=True)
    legacy_root = Path(current_app.static_folder) / "uploads"
    legacy_requested = (legacy_root / path).resolve()
    if (
        legacy_root.resolve() not in legacy_requested.parents
        or not legacy_requested.is_file()
    ):
        abort(404)
    return send_file(legacy_requested, conditional=True)


@media.get("/admin")
@media_permission("media.view")
def index():
    query = MediaAsset.query.filter(MediaAsset.status == "active")
    search = request.args.get("q", "").strip()
    module = request.args.get("module", "").strip()
    if search:
        query = query.filter(
            or_(
                MediaAsset.filename.ilike(f"%{search}%"),
                MediaAsset.original_filename.ilike(f"%{search}%"),
            )
        )
    if module:
        query = query.filter_by(module=module)
    page = query.order_by(MediaAsset.uploaded_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=24, error_out=False
    )
    totals = {
        "files": MediaAsset.query.filter_by(status="active").count(),
        "images": MediaAsset.query.filter(
            MediaAsset.status == "active", MediaAsset.mime_type.like("image/%")
        ).count(),
        "videos": MediaAsset.query.filter(
            MediaAsset.status == "active", MediaAsset.mime_type.like("video/%")
        ).count(),
        "documents": MediaAsset.query.filter(
            MediaAsset.status == "active",
            ~MediaAsset.mime_type.like("image/%"),
            ~MediaAsset.mime_type.like("video/%"),
        ).count(),
        "bytes": db_sum_size(),
    }
    duplicate_checksums = {
        checksum
        for checksum, count in db.session.query(
            MediaAsset.checksum, db.func.count(MediaAsset.id)
        )
        .filter_by(status="active")
        .group_by(MediaAsset.checksum)
        .having(db.func.count(MediaAsset.id) > 1)
        .all()
    }
    return render_template(
        "media/index.html",
        assets=page,
        totals=totals,
        selected_module=module,
        search=search,
        duplicate_checksums=duplicate_checksums,
        modules=(
            "properties",
            "developments",
            "developers",
            "agencies",
            "agents",
            "documents",
            "videos",
        ),
    )


@media.post("/admin/<int:asset_id>/delete")
@media_permission("media.delete")
def delete(asset_id):
    asset = MediaAsset.query.get_or_404(asset_id)
    MediaService.delete(asset)
    return redirect(url_for("media.index"))


@media.post("/admin/<int:asset_id>/replace")
@media_permission("media.edit")
def replace(asset_id):
    asset = MediaAsset.query.get_or_404(asset_id)
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return redirect(url_for("media.index"))
    try:
        MediaService.replace(asset, uploaded_file)
        db.session.commit()
    except ValueError:
        db.session.rollback()
    return redirect(url_for("media.index"))


def db_sum_size():
    from sqlalchemy import func

    return MediaAsset.query.with_entities(
        func.coalesce(func.sum(MediaAsset.file_size), 0)
    ).scalar()
