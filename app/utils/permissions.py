from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from app.admin.roles import has_permission


def require_permission(permission_key):
    """Require an authenticated user to have a permission."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not has_permission(current_user, permission_key):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
