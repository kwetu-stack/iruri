from flask import Blueprint, request
from flask_login import current_user

reports = Blueprint("reports", __name__, url_prefix="/reports")


@reports.before_request
def track_report_view():
    if (
        request.endpoint
        and request.endpoint.endswith("_dashboard")
        and getattr(current_user, "is_authenticated", False)
    ):
        from app.activities.service import record_activity

        record_activity(
            "View", "Reports", request.endpoint.rsplit(".", 1)[-1], request.path
        )


from app.reports import routes
