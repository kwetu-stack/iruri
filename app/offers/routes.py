from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.agents.models import Agent
from app.buyers.models import Buyer
from app.extensions import db
from app.offers import offers
from app.offers.models import OFFER_STATUSES, PropertyOffer
from app.properties.models import Property
from app.sellers.models import Seller


def _current_buyer():
    if not current_user.is_authenticated or not current_user.email:
        return None
    return Buyer.query.filter_by(email=current_user.email).first()


def _display_name(profile):
    return profile.full_name or profile.company_name or profile.email or "Unknown"


def _can_review(offer):
    if not current_user.is_authenticated:
        return False
    role = (current_user.role or "").lower()
    if role in {"admin", "administrator"}:
        return True
    email = (current_user.email or "").lower()
    seller_email = (offer.property.seller.email or "").lower()
    agent_emails = {
        (offer.property.agent.email or "").lower() if offer.property.agent else "",
        (offer.agent.email or "").lower() if offer.agent else "",
    }
    return bool(email) and (email == seller_email or email in agent_emails)


def _parse_amount(value):
    try:
        amount = Decimal(value.strip())
    except (AttributeError, InvalidOperation):
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount.quantize(Decimal("0.01"))


@offers.route("/create", methods=["GET", "POST"])
@login_required
def create():
    property_id = request.values.get("property_id", type=int)
    property = Property.query.get_or_404(property_id) if property_id else None
    properties = Property.query.order_by(Property.created_at.desc()).all()
    buyer = _current_buyer()
    if not buyer:
        flash("A buyer profile is required to submit an offer.", "danger")
        return redirect(url_for("properties.index"))

    if request.method == "POST":
        property_id = request.form.get("property_id", type=int)
        property = Property.query.get(property_id) if property_id else None
        amount = _parse_amount(request.form.get("offered_price", ""))
        currency = request.form.get("currency", "").strip().upper() or "KES"
        message = request.form.get("buyer_message", "").strip() or None
        if not property:
            flash("Property is required.", "danger")
        elif not amount:
            flash("Offer amount must be greater than zero.", "danger")
        elif not currency or len(currency) > 10:
            flash("Currency is required and must be at most 10 characters.", "danger")
        else:
            offer = PropertyOffer(
                offer_number="TEMP",
                property=property,
                buyer=buyer,
                offered_price=amount,
                currency=currency,
                buyer_message=message,
            )
            db.session.add(offer)
            db.session.flush()
            offer.offer_number = f"OFF-{datetime.utcnow().year}-{offer.id:06d}"
            db.session.commit()
            flash("Offer submitted successfully.", "success")
            return redirect(url_for("buyers.details", id=buyer.id))

    return render_template(
        "offers/create.html", property=property, properties=properties, buyer=buyer
    )


@offers.route("/<int:id>/review", methods=["GET", "POST"])
@login_required
def review(id):
    offer = PropertyOffer.query.get_or_404(id)
    if not _can_review(offer):
        flash("You are not authorized to review this offer.", "danger")
        return redirect(url_for("properties.details", id=offer.property_id))

    if request.method == "POST":
        status = request.form.get("status", "").strip()
        agent_id = request.form.get("agent_id", type=int)
        if status not in {
            "Accepted",
            "Rejected",
            "Under Review",
            "Withdrawn",
            "Expired",
        }:
            flash("Select a valid offer decision.", "danger")
        elif agent_id and not Agent.query.filter_by(id=agent_id).first():
            flash("Select a valid agent.", "danger")
        else:
            offer.status = status
            offer.agent_id = agent_id or None
            offer.seller_response = (
                request.form.get("seller_response", "").strip() or None
            )
            db.session.commit()
            flash("Offer updated successfully.", "success")
            return redirect(url_for("properties.details", id=offer.property_id))

    return render_template(
        "offers/review.html",
        offer=offer,
        agents=Agent.query.filter_by(is_active=True).order_by(Agent.agent_number).all(),
        statuses=("Under Review", "Accepted", "Rejected", "Withdrawn", "Expired"),
    )
