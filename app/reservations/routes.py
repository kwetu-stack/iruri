from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.buyers.models import Buyer
from app.extensions import db
from app.transactions.models import PropertyTransaction
from app.offers.models import PropertyOffer
from app.reservations import reservations
from app.reservations.models import PropertyReservation
from app.properties.models import Property
from app.audit.service import record_audit


def _is_admin():
    return (current_user.role or "").lower() in {"admin", "administrator"}


def _current_buyer():
    if not current_user.is_authenticated or not current_user.email:
        return None
    return Buyer.query.filter_by(email=current_user.email).first()


def _can_review(offer):
    if _is_admin():
        return True
    email = (current_user.email or "").lower()
    return bool(email) and email in {
        (offer.property.seller.email or "").lower(),
        (offer.property.agent.email or "").lower() if offer.property.agent else "",
        (offer.agent.email or "").lower() if offer.agent else "",
    }


def _can_access(reservation):
    if _is_admin():
        return True
    email = (current_user.email or "").lower()
    return bool(email) and email in {
        (reservation.buyer.email or "").lower(),
        (reservation.property.seller.email or "").lower(),
        (
            (reservation.property.agent.email or "").lower()
            if reservation.property.agent
            else ""
        ),
    }


def _sync_expiry(reservation):
    if reservation.status == "Active" and reservation.expiry_date <= datetime.utcnow():
        reservation.status = "Expired"
        if not PropertyReservation.query.filter(
            PropertyReservation.property_id == reservation.property_id,
            PropertyReservation.status == "Active",
            PropertyReservation.id != reservation.id,
        ).first():
            reservation.property.status = "Available"
        db.session.commit()


def _restore_property(reservation, status):
    reservation.status = status
    if status == "Completed":
        reservation.property.status = "Sold"
    elif not PropertyReservation.query.filter(
        PropertyReservation.property_id == reservation.property_id,
        PropertyReservation.status == "Active",
        PropertyReservation.id != reservation.id,
    ).first():
        reservation.property.status = "Available"


def _parse_fee(value):
    try:
        fee = Decimal((value or "").strip())
    except (AttributeError, InvalidOperation):
        return None
    if not fee.is_finite() or fee < 0:
        return None
    return fee.quantize(Decimal("0.01"))


def _parse_expiry(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d")
    except (AttributeError, ValueError):
        return None


@reservations.route("/")
@login_required
def index():
    reservation_list = PropertyReservation.query.order_by(
        PropertyReservation.created_at.desc()
    ).all()
    for reservation in reservation_list:
        _sync_expiry(reservation)
    return render_template(
        "reservations/index.html",
        reservations=reservation_list,
        total=len(reservation_list),
        active=sum(item.status == "Active" for item in reservation_list),
        completed=sum(item.status == "Completed" for item in reservation_list),
        expired=sum(item.status == "Expired" for item in reservation_list),
    )


@reservations.route("/create", defaults={"offer_id": None}, methods=["GET", "POST"])
@reservations.route("/create/<int:offer_id>", methods=["GET", "POST"])
@login_required
def create(offer_id):
    offer_id = offer_id or request.values.get("offer_id", type=int)
    if not offer_id:
        flash("An accepted offer is required to create a reservation.", "danger")
        return redirect(url_for("properties.index"))
    offer = PropertyOffer.query.get_or_404(offer_id)
    buyer = _current_buyer()
    if offer.status != "Accepted":
        flash("A reservation requires an accepted offer.", "danger")
        return redirect(url_for("offers.review", id=offer.id))
    if (
        offer.property.status == "Sold"
        or PropertyTransaction.query.filter_by(
            property_id=offer.property_id, transaction_status="Completed"
        ).first()
    ):
        flash("Sold properties do not accept new reservations.", "danger")
        return redirect(url_for("properties.details", id=offer.property_id))
    if not (buyer and buyer.id == offer.buyer_id) and not _can_review(offer):
        flash("You are not authorized to create this reservation.", "danger")
        return redirect(url_for("properties.details", id=offer.property_id))
    if offer.reservation:
        return redirect(url_for("reservations.details", id=offer.reservation.id))

    reservation_date = datetime.utcnow()
    if request.method == "POST":
        fee = _parse_fee(request.form.get("reservation_fee"))
        expiry_date = _parse_expiry(request.form.get("expiry_date"))
        currency = request.form.get("currency", "").strip().upper() or offer.currency
        if fee is None:
            flash("Reservation fee must be greater than or equal to zero.", "danger")
        elif not expiry_date or expiry_date <= reservation_date:
            flash("Expiry date must be after the reservation date.", "danger")
        elif not currency or len(currency) > 10:
            flash("Currency is required and must be at most 10 characters.", "danger")
        elif PropertyReservation.query.filter_by(
            property_id=offer.property_id, status="Active"
        ).first():
            flash("Property Already Reserved", "danger")
        else:
            reservation = PropertyReservation(
                reservation_number="TEMP",
                property=offer.property,
                buyer=offer.buyer,
                property_offer=offer,
                reserved_by=current_user.email or current_user.get_id(),
                reservation_date=reservation_date,
                expiry_date=expiry_date,
                reservation_fee=fee,
                currency=currency,
                status="Active",
                notes=request.form.get("notes", "").strip() or None,
            )
            offer.property.status = "Reserved"
            db.session.add(reservation)
            try:
                db.session.flush()
                reservation.reservation_number = (
                    f"RES-{datetime.utcnow().year}-{reservation.id:06d}"
                )
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Property Already Reserved", "danger")
            else:
                record_audit(
                    "Create",
                    "Transactions",
                    f"Reservation {reservation.reservation_number} created",
                    "Reservation",
                    reservation.id,
                )
                flash("Reservation created successfully.", "success")
                return redirect(url_for("reservations.details", id=reservation.id))

    return render_template(
        "reservations/create.html", offer=offer, reservation_date=reservation_date
    )


@reservations.route("/<int:id>")
@login_required
def details(id):
    reservation = PropertyReservation.query.get_or_404(id)
    if not _can_access(reservation):
        flash("You are not authorized to view this reservation.", "danger")
        return redirect(url_for("properties.details", id=reservation.property_id))
    _sync_expiry(reservation)
    return render_template("reservations/details.html", reservation=reservation)


@reservations.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    reservation = PropertyReservation.query.get_or_404(id)
    if not _can_access(reservation):
        flash("You are not authorized to cancel this reservation.", "danger")
    elif reservation.status not in {"Pending", "Active"}:
        flash("This reservation cannot be cancelled.", "danger")
    else:
        _restore_property(reservation, "Cancelled")
        db.session.commit()
        flash("Reservation cancelled successfully.", "success")
    return redirect(url_for("reservations.details", id=id))


@reservations.route("/<int:id>/complete", methods=["POST"])
@login_required
def complete(id):
    reservation = PropertyReservation.query.get_or_404(id)
    if not _can_access(reservation):
        flash("You are not authorized to complete this reservation.", "danger")
    elif reservation.status != "Active":
        flash("Only an active reservation can be completed.", "danger")
    else:
        _restore_property(reservation, "Completed")
        db.session.commit()
        flash("Reservation marked completed.", "success")
    return redirect(url_for("reservations.details", id=id))


@reservations.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    reservation = PropertyReservation.query.get_or_404(id)
    if not _is_admin():
        flash("Only administrators can delete reservations.", "danger")
    else:
        db.session.delete(reservation)
        db.session.commit()
        flash("Reservation deleted successfully.", "success")
        return redirect(url_for("reservations.index"))
    return redirect(url_for("reservations.details", id=id))
