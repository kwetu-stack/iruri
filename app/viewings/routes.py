from datetime import date, datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.agents.models import Agent
from app.buyers.models import Buyer
from app.extensions import db
from app.properties.models import Property
from app.viewings import viewings
from app.viewings.models import VIEWING_STATUSES, ViewingRequest


def _form_data():
    try:
        requested_date = datetime.strptime(
            request.form.get("requested_date", ""), "%Y-%m-%d"
        ).date()
        requested_time = datetime.strptime(
            request.form.get("requested_time", ""), "%H:%M"
        ).time()
    except ValueError:
        return None, None, "A valid preferred date and time are required."
    if requested_date < date.today():
        return None, None, "The viewing date cannot be in the past."
    return requested_date, requested_time, None


def _form_context(viewing_request=None):
    return {
        "viewing_request": viewing_request,
        "today": date.today(),
        "buyers": Buyer.query.order_by(Buyer.full_name, Buyer.company_name).all(),
        "properties": Property.query.order_by(Property.title).all(),
        "agents": Agent.query.filter_by(is_active=True)
        .order_by(Agent.first_name)
        .all(),
        "statuses": VIEWING_STATUSES,
    }


@viewings.route("/")
@login_required
def index():
    requests_list = ViewingRequest.query.order_by(
        ViewingRequest.requested_date.asc(), ViewingRequest.requested_time.asc()
    ).all()
    return render_template("viewings/index.html", viewing_requests=requests_list)


@viewings.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        buyer_id = request.form.get("buyer_id", type=int)
        property_id = request.form.get("property_id", type=int)
        buyer = db.session.get(Buyer, buyer_id) if buyer_id else None
        property = db.session.get(Property, property_id) if property_id else None
        requested_date, requested_time, error = _form_data()
        if not buyer or not property:
            error = "Buyer and property are required."
        if error:
            flash(error, "danger")
            return render_template("viewings/create.html", **_form_context())
        viewing_request = ViewingRequest(
            request_number="TEMP",
            buyer=buyer,
            property=property,
            requested_date=requested_date,
            requested_time=requested_time,
            message=request.form.get("message", "").strip() or None,
        )
        db.session.add(viewing_request)
        db.session.flush()
        viewing_request.request_number = (
            f"VR-{datetime.utcnow().year}-{viewing_request.id:06d}"
        )
        db.session.commit()
        flash("Viewing request submitted successfully.", "success")
        return redirect(url_for("viewings.index"))
    return render_template("viewings/create.html", **_form_context())


@viewings.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    viewing_request = ViewingRequest.query.get_or_404(id)
    if request.method == "POST":
        status = request.form.get("status", "").strip()
        agent_id = request.form.get("agent_id", type=int)
        if status not in VIEWING_STATUSES:
            flash("Select a valid viewing status.", "danger")
            return render_template(
                "viewings/edit.html", **_form_context(viewing_request)
            )
        viewing_request.status = status
        viewing_request.agent = db.session.get(Agent, agent_id) if agent_id else None
        viewing_request.admin_notes = (
            request.form.get("admin_notes", "").strip() or None
        )
        db.session.commit()
        flash("Viewing request updated successfully.", "success")
        return redirect(url_for("viewings.index"))
    return render_template("viewings/edit.html", **_form_context(viewing_request))


@viewings.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):
    viewing_request = ViewingRequest.query.get_or_404(id)
    if request.method == "POST":
        db.session.delete(viewing_request)
        db.session.commit()
        flash("Viewing request deleted successfully.", "success")
        return redirect(url_for("viewings.index"))
    return render_template("viewings/delete.html", viewing_request=viewing_request)
