from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from app.agents.models import Agent
from app.audit.service import record_audit
from app.extensions import db
from app.leads import leads
from app.leads.models import LEAD_STATUSES, Lead
from app.notifications.service import notify_profile
from app.properties.models import Property
from app.utils.permissions import require_permission


def _date_filter(value, end_of_day=False):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    if end_of_day:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed


@leads.route("/")
@leads.route("/", strict_slashes=False)
@require_permission("lead.view")
def index():
    selected_status = request.args.get("status", "").strip()
    selected_agent = request.args.get("agent_id", type=int)
    selected_property = request.args.get("property_id", type=int)
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    query = Lead.query
    if selected_status in LEAD_STATUSES:
        query = query.filter_by(status=selected_status)
    if selected_agent:
        query = query.filter_by(agent_id=selected_agent)
    if selected_property:
        query = query.filter_by(property_id=selected_property)
    if search:
        query = query.filter(
            db.or_(
                Lead.reference_number.ilike(f"%{search}%"),
                Lead.name.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
            )
        )
    parsed_from = _date_filter(date_from)
    parsed_to = _date_filter(date_to, end_of_day=True)
    if date_from and parsed_from is None:
        flash("Use YYYY-MM-DD for the start date.", "danger")
    if date_to and parsed_to is None:
        flash("Use YYYY-MM-DD for the end date.", "danger")
    if parsed_from:
        query = query.filter(Lead.created_at >= parsed_from)
    if parsed_to:
        query = query.filter(Lead.created_at <= parsed_to)

    lead_list = query.order_by(Lead.created_at.desc(), Lead.id.desc()).all()
    stats = {
        "total": Lead.query.count(),
        "new": Lead.query.filter_by(status="New").count(),
        "follow_up": Lead.query.filter(Lead.status.in_(("New", "Contacted"))).count(),
        "closed": Lead.query.filter_by(status="Closed").count(),
    }
    return render_template(
        "leads/index.html",
        leads=lead_list,
        agents=Agent.query.filter_by(is_active=True).order_by(Agent.first_name).all(),
        properties=Property.query.order_by(Property.title).all(),
        statuses=LEAD_STATUSES,
        stats=stats,
        selected_status=selected_status,
        selected_agent=selected_agent,
        selected_property=selected_property,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@leads.get("/<int:lead_id>")
@require_permission("lead.view")
def detail(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return render_template(
        "leads/detail.html",
        lead=lead,
        statuses=LEAD_STATUSES,
        agents=Agent.query.filter_by(is_active=True).order_by(Agent.first_name).all(),
    )


@leads.post("/<int:lead_id>/status")
@require_permission("lead.edit")
def status_update(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    status = request.form.get("status", "").strip()
    if status not in LEAD_STATUSES:
        flash("Choose a valid lead status.", "danger")
        return redirect(url_for("leads.detail", lead_id=lead.id))
    previous_status = lead.status
    lead.status = status
    db.session.commit()
    action = "Lead closed" if status == "Closed" else "Lead updated"
    record_audit(
        action,
        "Leads",
        f"Lead {lead.reference_number} status changed from {previous_status} to {status}",
        "Lead",
        lead.id,
    )
    flash("Lead status updated.", "success")
    return redirect(url_for("leads.detail", lead_id=lead.id))


@leads.post("/<int:lead_id>/assignment")
@require_permission("lead.assign")
def assignment(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    agent_id = request.form.get("agent_id", type=int)
    agent = (
        Agent.query.filter_by(id=agent_id, is_active=True).first() if agent_id else None
    )
    if agent_id and agent is None:
        flash("Choose an active agent.", "danger")
        return redirect(url_for("leads.detail", lead_id=lead.id))
    lead.agent_id = agent.id if agent else None
    db.session.commit()
    record_audit(
        "Lead assigned",
        "Leads",
        f"Lead {lead.reference_number} assigned to {agent.full_name if agent else 'Unassigned'}",
        "Lead",
        lead.id,
    )
    if agent:
        notify_profile(
            agent,
            title="Lead assigned to you",
            message=f"Lead {lead.reference_number} has been assigned to you.",
            notification_type="Information",
            priority="High",
            action_url=url_for("leads.detail", lead_id=lead.id),
            related_module="Leads",
            related_record_id=lead.id,
        )
        db.session.commit()
    flash("Lead assignment updated.", "success")
    return redirect(url_for("leads.detail", lead_id=lead.id))
