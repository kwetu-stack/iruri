from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.agents.models import Agent
from app.buyers.models import Buyer
from app.extensions import db
from app.offers import offers
from app.offers.models import OFFER_STATUSES, OfferNegotiation, PropertyOffer
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


TERMINAL_STATUSES = {"Accepted", "Rejected", "Withdrawn", "Expired"}
VALID_TRANSITIONS = {
    "Pending": {"Under Review", "Accepted", "Rejected", "Withdrawn", "Expired"},
    "Under Review": {"Counter Offered", "Accepted", "Rejected", "Withdrawn", "Expired"},
    "Counter Offered": {
        "Counter Offered",
        "Accepted",
        "Rejected",
        "Withdrawn",
        "Expired",
    },
}


def _current_buyer_can_act(offer):
    buyer = _current_buyer()
    return buyer is not None and buyer.id == offer.buyer_id


def _actor_for(offer):
    if _current_buyer_can_act(offer) and offer.status == "Counter Offered":
        return "Buyer"
    if _can_review(offer):
        return (
            "Administrator"
            if (current_user.role or "").lower() in {"admin", "administrator"}
            else "Seller"
        )
    return None


def _active_offer(offer):
    return offer.status not in TERMINAL_STATUSES


def _change_status(offer, status):
    return status in VALID_TRANSITIONS.get(offer.status, set())


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
    if not (_can_review(offer) or _current_buyer_can_act(offer)):
        flash("You are not authorized to view this offer.", "danger")
        return redirect(url_for("properties.details", id=offer.property_id))

    if request.method == "POST":
        status = request.form.get("status", "").strip()
        agent_id = request.form.get("agent_id", type=int)
        if not _change_status(offer, status):
            flash(f"An offer cannot move from {offer.status} to {status}.", "danger")
        elif status not in OFFER_STATUSES:
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
        can_review=_can_review(offer),
        can_buyer_act=_current_buyer_can_act(offer),
        agents=Agent.query.filter_by(is_active=True).order_by(Agent.agent_number).all(),
        statuses=tuple(VALID_TRANSITIONS.get(offer.status, set())),
    )


@offers.route("/<int:id>/counter", methods=["GET", "POST"])
@offers.route("/<int:id>/counter-offer", methods=["GET", "POST"])
@login_required
def counter_offer(id):
    offer = PropertyOffer.query.get_or_404(id)
    actor = _actor_for(offer)
    if not actor:
        flash("You are not authorized to negotiate this offer.", "danger")
        return redirect(url_for("properties.details", id=offer.property_id))
    if not _active_offer(offer):
        flash("This offer is no longer open for negotiation.", "danger")
        return redirect(url_for("offers.review", id=offer.id))

    if request.method == "POST":
        amount = _parse_amount(request.form.get("offered_amount", ""))
        if not amount:
            flash("Counter amount must be greater than zero.", "danger")
        else:
            db.session.add(
                OfferNegotiation(
                    property_offer=offer,
                    offered_by=actor,
                    offered_amount=amount,
                    message=request.form.get("message", "").strip() or None,
                )
            )
            offer.offered_price = amount
            offer.status = "Counter Offered"
            db.session.commit()
            flash("Counter offer submitted successfully.", "success")
            return redirect(url_for("offers.review", id=offer.id))

    return render_template("offers/counter_offer.html", offer=offer)


def _action(id, action):
    offer = PropertyOffer.query.get_or_404(id)
    buyer_action = action == "Withdrawn" or (
        action in {"Accepted", "Rejected"} and offer.status == "Counter Offered"
    )
    authorized = _current_buyer_can_act(offer) if buyer_action else _can_review(offer)
    if not authorized:
        flash("You are not authorized to perform this action.", "danger")
    elif not _active_offer(offer) or not _change_status(offer, action):
        flash("This offer cannot be changed from its current status.", "danger")
    else:
        offer.status = action
        db.session.commit()
        flash(f"Offer {action.lower()} successfully.", "success")
    return redirect(url_for("offers.review", id=offer.id))


@offers.route("/<int:id>/accept", methods=["POST"])
@login_required
def accept(id):
    return _action(id, "Accepted")


@offers.route("/<int:id>/reject", methods=["POST"])
@login_required
def reject(id):
    return _action(id, "Rejected")


@offers.route("/<int:id>/withdraw", methods=["POST"])
@login_required
def withdraw(id):
    return _action(id, "Withdrawn")
