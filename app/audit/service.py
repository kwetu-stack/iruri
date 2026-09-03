from datetime import datetime
from uuid import uuid4

from flask import has_request_context, request
from flask_login import current_user

from app.audit.models import AuditLog
from app.extensions import db


def record_audit(
    action,
    module,
    description,
    entity_type=None,
    entity_id=None,
    status="Success",
    commit=True,
):
    if not action or not module:
        raise ValueError("Audit action and module are required")

    authenticated = bool(getattr(current_user, "is_authenticated", False))
    event = AuditLog(
        event_number=f"AUD-{datetime.utcnow().year}-{uuid4().hex[:16].upper()}",
        user_id=current_user.id if authenticated else None,
        username=(
            (
                getattr(current_user, "email", None)
                or getattr(current_user, "username", None)
                or "System"
            )
            if authenticated
            else "System"
        ),
        action=action,
        module=module,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        description=description,
        ip_address=request.remote_addr if has_request_context() else None,
        user_agent=request.user_agent.string if has_request_context() else None,
        request_method=request.method if has_request_context() else None,
        request_path=request.path if has_request_context() else None,
        status=status,
    )
    db.session.add(event)
    if commit:
        db.session.commit()
    return event
