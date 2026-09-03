from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.reservations.models import PropertyReservation
from app.sale_agreements import sale_agreements
from app.sale_agreements.models import (
    AGREEMENT_STATUSES,
    PAYMENT_METHODS,
    PAYMENT_TYPES,
    PropertyPayment,
    SaleAgreement,
)
from app.transactions.models import PropertyTransaction


def _is_admin():
    return (current_user.role or "").lower() in {"admin", "administrator"}


def _can_access(agreement):
    if _is_admin():
        return True
    email = (current_user.email or "").lower()
    return bool(email) and email in {
        (agreement.buyer.email or "").lower(),
        (agreement.seller.email or "").lower(),
        (
            (agreement.property.agent.email or "").lower()
            if agreement.property.agent
            else ""
        ),
    }


def _can_access_reservation(reservation):
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


def _parse_price(value):
    try:
        price = Decimal((value or "").strip())
    except (AttributeError, InvalidOperation):
        return None
    if not price.is_finite() or price <= 0:
        return None
    return price.quantize(Decimal("0.01"))


def _parse_date(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except (AttributeError, ValueError):
        return None


def _parse_amount(value):
    try:
        amount = Decimal((value or "").strip())
    except (AttributeError, InvalidOperation):
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount.quantize(Decimal("0.01"))


def _payment_values(form, agreement):
    payment_date = _parse_date(form.get("payment_date"))
    payment_type = form.get("payment_type", "").strip()
    payment_method = form.get("payment_method", "").strip()
    amount = _parse_amount(form.get("amount"))
    currency = form.get("currency", "").strip().upper()
    if not payment_date:
        return None, "Payment date is required."
    if payment_type not in PAYMENT_TYPES:
        return None, "Select a valid payment type."
    if payment_method not in PAYMENT_METHODS:
        return None, "Select a valid payment method."
    if amount is None:
        return None, "Amount must be greater than zero."
    if currency != agreement.currency.upper():
        return None, "Payment currency must match the agreement currency."
    return {
        "payment_date": payment_date,
        "payment_type": payment_type,
        "payment_method": payment_method,
        "reference_number": form.get("reference_number", "").strip() or None,
        "amount": amount,
        "currency": currency,
        "notes": form.get("notes", "").strip() or None,
        "receipt_number": form.get("receipt_number", "").strip() or None,
    }, None


def _payment_error(agreement, values, payment=None):
    existing = [item for item in agreement.payments if item is not payment]
    received = sum(
        (item.amount for item in existing if item.payment_type != "Refund"),
        Decimal("0.00"),
    )
    refunds = sum(
        (item.amount for item in existing if item.payment_type == "Refund"),
        Decimal("0.00"),
    )
    if values["payment_type"] == "Refund":
        if values["amount"] > received - refunds:
            return "Refund cannot exceed the amount previously received."
    elif received - refunds + values["amount"] > Decimal(agreement.agreed_price):
        return "Total payments cannot exceed the agreed purchase price."
    if (
        values["receipt_number"]
        and PropertyPayment.query.filter(
            PropertyPayment.receipt_number == values["receipt_number"],
            PropertyPayment.id != (payment.id if payment else None),
        ).first()
    ):
        return "Receipt number must be unique."
    return None


def _recalculate_agreement(agreement):
    if agreement.total_paid >= Decimal(agreement.agreed_price):
        agreement.status = "Completed"
        agreement.property.status = "Ready for Transfer"
    elif agreement.status == "Completed":
        agreement.status = "Active"
        agreement.property.status = "Under Sale Agreement"


def _render_payment_form(agreement, payment=None):
    return render_template(
        "sale_agreements/payment_form.html",
        agreement=agreement,
        payment=payment,
        payment_types=PAYMENT_TYPES,
        payment_methods=PAYMENT_METHODS,
        today=date.today().isoformat(),
    )


def _form_values(form, default_currency="KES"):
    agreement_date = _parse_date(form.get("agreement_date"))
    completion_date = _parse_date(form.get("completion_date"))
    currency = form.get("currency", "").strip().upper() or default_currency
    price = _parse_price(form.get("agreed_price"))
    if price is None:
        return None, "Agreed price must be greater than zero."
    if not agreement_date or not completion_date:
        return None, "Agreement date and completion date are required."
    if completion_date < agreement_date:
        return None, "Completion date cannot be earlier than agreement date."
    if not currency or len(currency) > 10:
        return None, "Currency is required and must be at most 10 characters."
    return {
        "agreed_price": price,
        "currency": currency,
        "agreement_date": agreement_date,
        "completion_date": completion_date,
        "notes": form.get("notes", "").strip() or None,
    }, None


def _render_form(agreement=None, reservation=None):
    return render_template(
        "sale_agreements/form.html",
        agreement=agreement,
        reservation=reservation or agreement.reservation,
        today=date.today().isoformat(),
    )


@sale_agreements.route("/")
@login_required
def index():
    agreements = SaleAgreement.query.order_by(SaleAgreement.created_at.desc()).all()
    return render_template(
        "sale_agreements/index.html",
        agreements=agreements,
        total=len(agreements),
        draft=sum(item.status == "Draft" for item in agreements),
        active=sum(item.status == "Active" for item in agreements),
        completed=sum(item.status == "Completed" for item in agreements),
        cancelled=sum(item.status == "Cancelled" for item in agreements),
    )


@sale_agreements.route("/create/<int:reservation_id>", methods=["GET", "POST"])
@login_required
def create(reservation_id):
    reservation = PropertyReservation.query.get_or_404(reservation_id)
    if not _can_access_reservation(reservation):
        flash("You are not authorized to create this agreement.", "danger")
        return redirect(url_for("reservations.details", id=reservation.id))
    if reservation.status != "Active":
        flash("A sale agreement requires an active reservation.", "danger")
        return redirect(url_for("reservations.details", id=reservation.id))
    if (
        reservation.property.status == "Sold"
        or PropertyTransaction.query.filter_by(
            property_id=reservation.property_id, transaction_status="Completed"
        ).first()
    ):
        flash("Sold properties do not accept new sale agreements.", "danger")
        return redirect(url_for("properties.details", id=reservation.property_id))
    if SaleAgreement.query.filter_by(
        reservation_id=reservation.id, status="Active"
    ).first():
        flash("An active sale agreement already exists for this reservation.", "danger")
        return redirect(url_for("reservations.details", id=reservation.id))
    if request.method == "POST":
        values, error = _form_values(request.form, reservation.currency)
        if not error:
            agreement = SaleAgreement(
                agreement_number="TEMP",
                reservation=reservation,
                property=reservation.property,
                buyer=reservation.buyer,
                seller=reservation.property.seller,
                **values,
            )
            db.session.add(agreement)
            try:
                db.session.flush()
                agreement.agreement_number = (
                    f"AGR-{datetime.utcnow().year}-{agreement.id:06d}"
                )
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                error = "An active sale agreement already exists for this reservation."
            else:
                flash("Sale agreement created successfully.", "success")
                return redirect(url_for("sale_agreements.details", id=agreement.id))
        flash(error, "danger")
    return _render_form(reservation=reservation)


@sale_agreements.route("/<int:id>")
@login_required
def details(id):
    agreement = SaleAgreement.query.get_or_404(id)
    if not _can_access(agreement):
        flash("You are not authorized to view this agreement.", "danger")
        return redirect(url_for("properties.details", id=agreement.property_id))
    return render_template("sale_agreements/details.html", agreement=agreement)


@sale_agreements.route("/payments")
@login_required
def payments_index():
    payments = PropertyPayment.query.order_by(
        PropertyPayment.payment_date.desc(), PropertyPayment.id.desc()
    ).all()
    visible = [payment for payment in payments if _can_access(payment.sale_agreement)]
    agreements = [
        agreement for agreement in SaleAgreement.query.all() if _can_access(agreement)
    ]
    return render_template(
        "sale_agreements/payments.html",
        payments=visible,
        total_transactions=len(visible),
        total_received=sum(
            (payment.amount for payment in visible if payment.payment_type != "Refund"),
            Decimal("0.00"),
        ),
        outstanding_balance=sum(
            (agreement.outstanding_balance for agreement in agreements), Decimal("0.00")
        ),
        completed_payments=sum(
            payment.payment_type == "Final Payment" for payment in visible
        ),
        pending_balance=sum(
            (
                agreement.outstanding_balance
                for agreement in agreements
                if agreement.status == "Active"
            ),
            Decimal("0.00"),
        ),
    )


@sale_agreements.route("/<int:id>/payments/create", methods=["GET", "POST"])
@login_required
def payment_create(id):
    agreement = SaleAgreement.query.get_or_404(id)
    if not _can_access(agreement):
        flash("You are not authorized to record payments for this agreement.", "danger")
        return redirect(url_for("sale_agreements.details", id=id))
    if agreement.status != "Active":
        flash("Payments can only be recorded for active agreements.", "danger")
        return redirect(url_for("sale_agreements.details", id=id))
    if request.method == "POST":
        values, error = _payment_values(request.form, agreement)
        if not error:
            error = _payment_error(agreement, values)
        if not error:
            payment = PropertyPayment(
                payment_number="TEMP",
                sale_agreement=agreement,
                received_by=current_user.email,
                **values,
            )
            db.session.add(payment)
            db.session.flush()
            payment.payment_number = f"PAY-{datetime.utcnow().year}-{payment.id:06d}"
            _recalculate_agreement(agreement)
            db.session.commit()
            flash("Payment recorded successfully.", "success")
            return redirect(url_for("sale_agreements.payment_details", id=payment.id))
        flash(error, "danger")
    return _render_payment_form(agreement)


@sale_agreements.route("/payments/<int:id>")
@login_required
def payment_details(id):
    payment = PropertyPayment.query.get_or_404(id)
    if not _can_access(payment.sale_agreement):
        flash("You are not authorized to view this payment.", "danger")
        return redirect(url_for("sale_agreements.index"))
    return render_template("sale_agreements/payment_details.html", payment=payment)


@sale_agreements.route("/payments/<int:id>/edit", methods=["GET", "POST"])
@login_required
def payment_edit(id):
    payment = PropertyPayment.query.get_or_404(id)
    agreement = payment.sale_agreement
    if not _can_access(agreement):
        flash("You are not authorized to edit this payment.", "danger")
        return redirect(url_for("sale_agreements.payment_details", id=id))
    if request.method == "POST":
        values, error = _payment_values(request.form, agreement)
        if not error:
            error = _payment_error(agreement, values, payment)
        if not error:
            for field, value in values.items():
                setattr(payment, field, value)
            _recalculate_agreement(agreement)
            db.session.commit()
            flash("Payment updated successfully.", "success")
            return redirect(url_for("sale_agreements.payment_details", id=id))
        flash(error, "danger")
    return _render_payment_form(agreement, payment)


@sale_agreements.route("/payments/<int:id>/delete", methods=["POST"])
@login_required
def payment_delete(id):
    payment = PropertyPayment.query.get_or_404(id)
    agreement = payment.sale_agreement
    if not _is_admin():
        flash("Only administrators can delete payments.", "danger")
    else:
        db.session.delete(payment)
        db.session.flush()
        _recalculate_agreement(agreement)
        db.session.commit()
        flash("Payment deleted successfully.", "success")
    return redirect(url_for("sale_agreements.details", id=agreement.id))


@sale_agreements.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    agreement = SaleAgreement.query.get_or_404(id)
    if not _can_access(agreement):
        flash("You are not authorized to edit this agreement.", "danger")
        return redirect(url_for("sale_agreements.details", id=id))
    if agreement.status != "Draft":
        flash("Only draft agreements can be edited.", "danger")
        return redirect(url_for("sale_agreements.details", id=id))
    if request.method == "POST":
        values, error = _form_values(request.form, agreement.currency)
        if not error:
            for field, value in values.items():
                setattr(agreement, field, value)
            db.session.commit()
            flash("Sale agreement updated successfully.", "success")
            return redirect(url_for("sale_agreements.details", id=id))
        flash(error, "danger")
    return _render_form(agreement=agreement)


def _change_status(id, target, allowed, message):
    agreement = SaleAgreement.query.get_or_404(id)
    if not _can_access(agreement):
        flash("You are not authorized to update this agreement.", "danger")
    elif agreement.status not in allowed:
        flash(f"This agreement cannot be marked {target.lower()}.", "danger")
    elif (
        target == "Active"
        and SaleAgreement.query.filter(
            SaleAgreement.reservation_id == agreement.reservation_id,
            SaleAgreement.status == "Active",
            SaleAgreement.id != agreement.id,
        ).first()
    ):
        flash("An active sale agreement already exists for this reservation.", "danger")
    else:
        agreement.status = target
        if target == "Active":
            agreement.property.status = "Under Sale Agreement"
        elif target == "Completed":
            agreement.property.status = "Sold"
        db.session.commit()
        flash(message, "success")
    return redirect(url_for("sale_agreements.details", id=id))


@sale_agreements.route("/<int:id>/activate", methods=["POST"])
@login_required
def activate(id):
    return _change_status(
        id, "Active", {"Draft", "Pending Signatures"}, "Sale agreement marked active."
    )


@sale_agreements.route("/<int:id>/complete", methods=["POST"])
@login_required
def complete(id):
    agreement = SaleAgreement.query.get_or_404(id)
    if not _can_access(agreement):
        flash("You are not authorized to update this agreement.", "danger")
    elif agreement.status != "Active":
        flash("Only active agreements can be marked completed.", "danger")
    elif agreement.outstanding_balance != Decimal("0.00"):
        flash("The outstanding payment balance must be zero first.", "danger")
    elif not agreement.commissions or any(
        item.payment_status != "Paid" for item in agreement.commissions
    ):
        flash("All commissions must be fully paid first.", "danger")
    else:
        agreement.status = "Completed"
        agreement.property.status = "Ready for Transfer"
        db.session.commit()
        flash("Sale agreement marked completed.", "success")
    return redirect(url_for("sale_agreements.details", id=id))


@sale_agreements.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    return _change_status(
        id,
        "Cancelled",
        {"Draft", "Pending Signatures", "Active"},
        "Sale agreement cancelled.",
    )
