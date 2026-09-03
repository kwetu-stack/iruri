from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.agencies.models import Agency
from app.agents.models import Agent
from app.commissions import commissions
from app.commissions.models import (
    COMMISSION_STATUSES,
    COMMISSION_TYPES,
    CommissionPayment,
    PropertyCommission,
)
from app.extensions import db
from app.sale_agreements.models import SaleAgreement


def _is_admin():
    return (current_user.role or "").lower() in {"admin", "administrator"}


def _can_access(commission):
    if _is_admin():
        return True
    email = (current_user.email or "").lower()
    recipients = [commission.seller.email if commission.seller else None]
    recipients.extend(
        [
            commission.agent.email if commission.agent else None,
            commission.agency.email if commission.agency else None,
        ]
    )
    return bool(email) and email in {(item or "").lower() for item in recipients}


def _decimal(value, positive=False):
    try:
        number = Decimal((value or "").strip())
    except (AttributeError, InvalidOperation):
        return None
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        return None
    return number


def _commission_values(form, agreement):
    commission_type = form.get("commission_type", "").strip()
    rate = _decimal(form.get("commission_rate"))
    sale_price = _decimal(form.get("sale_price"), positive=True)
    if commission_type not in COMMISSION_TYPES:
        return None, "Select a valid commission type."
    if rate is None or rate > 100:
        return None, "Commission rate must be between 0 and 100."
    if sale_price is None:
        return None, "Sale price must be greater than zero."
    agent_id = request.form.get("agent_id", "").strip() or None
    agency_id = request.form.get("agency_id", "").strip() or None
    try:
        agent = Agent.query.get(int(agent_id)) if agent_id else None
        agency = Agency.query.get(int(agency_id)) if agency_id else None
    except (TypeError, ValueError):
        agent = agency = None
    if commission_type == "Agent Commission" and not agent:
        return None, "Select an agent recipient."
    if commission_type == "Agency Commission" and not agency:
        return None, "Select an agency recipient."
    amount = (sale_price * rate / Decimal("100")).quantize(Decimal("0.01"))
    return {
        "commission_type": commission_type,
        "commission_rate": rate.quantize(Decimal("0.0001")),
        "sale_price": sale_price.quantize(Decimal("0.01")),
        "commission_amount": amount,
        "amount_paid": Decimal("0.00"),
        "balance": amount,
        "payment_status": "Pending",
        "agent": agent,
        "agency": agency,
        "notes": form.get("notes", "").strip() or None,
    }, None


@commissions.route("/")
@login_required
def index():
    all_commissions = PropertyCommission.query.order_by(
        PropertyCommission.created_at.desc()
    ).all()
    visible = [item for item in all_commissions if _can_access(item)]
    total = sum(
        (
            Decimal(item.commission_amount)
            for item in visible
            if item.payment_status != "Cancelled"
        ),
        Decimal("0.00"),
    )
    paid = sum(
        (
            Decimal(item.amount_paid)
            for item in visible
            if item.payment_status != "Cancelled"
        ),
        Decimal("0.00"),
    )
    pending = sum(
        (Decimal(item.balance) for item in visible if item.payment_status == "Pending"),
        Decimal("0.00"),
    )
    return render_template(
        "commissions/index.html",
        commissions=visible,
        total_generated=total,
        total_paid=paid,
        outstanding=total - paid,
        paid_count=sum(item.payment_status == "Paid" for item in visible),
        pending_count=sum(item.payment_status == "Pending" for item in visible),
    )


@commissions.route(
    "/sale-agreements/<int:agreement_id>/create", methods=["GET", "POST"]
)
@login_required
def create(agreement_id):
    agreement = SaleAgreement.query.get_or_404(agreement_id)
    if agreement.status != "Completed":
        flash("Commissions can only be generated for completed agreements.", "danger")
        return redirect(url_for("sale_agreements.details", id=agreement.id))
    if request.method == "POST":
        values, error = _commission_values(request.form, agreement)
        if not error:
            commission = PropertyCommission(
                commission_number="TEMP",
                sale_agreement=agreement,
                property=agreement.property,
                seller=agreement.seller,
                **values,
            )
            db.session.add(commission)
            db.session.flush()
            commission.commission_number = (
                f"COM-{datetime.utcnow().year}-{commission.id:06d}"
            )
            db.session.commit()
            flash("Commission generated successfully.", "success")
            return redirect(url_for("commissions.details", id=commission.id))
        flash(error, "danger")
    return render_template(
        "commissions/form.html",
        commission=None,
        agreement=agreement,
        commission_types=COMMISSION_TYPES,
        agents=Agent.query.order_by(Agent.first_name).all(),
        agencies=Agency.query.order_by(Agency.agency_name).all(),
    )


@commissions.route("/<int:id>")
@login_required
def details(id):
    commission = PropertyCommission.query.get_or_404(id)
    if not _can_access(commission):
        flash("You are not authorized to view this commission.", "danger")
        return redirect(url_for("commissions.index"))
    return render_template("commissions/details.html", commission=commission)


@commissions.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    commission = PropertyCommission.query.get_or_404(id)
    if (
        not _can_access(commission)
        or commission.payments
        or commission.payment_status == "Cancelled"
    ):
        flash("Only unpaid commissions may be edited by an authorized user.", "danger")
        return redirect(url_for("commissions.details", id=id))
    if request.method == "POST":
        values, error = _commission_values(request.form, commission.sale_agreement)
        if not error:
            for field in (
                "commission_type",
                "commission_rate",
                "sale_price",
                "commission_amount",
                "amount_paid",
                "balance",
                "payment_status",
                "notes",
            ):
                setattr(commission, field, values[field])
            commission.agent, commission.agency = values["agent"], values["agency"]
            db.session.commit()
            flash("Commission updated successfully.", "success")
            return redirect(url_for("commissions.details", id=id))
        flash(error, "danger")
    return render_template(
        "commissions/form.html",
        commission=commission,
        agreement=commission.sale_agreement,
        commission_types=COMMISSION_TYPES,
        agents=Agent.query.order_by(Agent.first_name).all(),
        agencies=Agency.query.order_by(Agency.agency_name).all(),
    )


@commissions.route("/<int:id>/payments/create", methods=["GET", "POST"])
@login_required
def payment_create(id):
    commission = PropertyCommission.query.get_or_404(id)
    if not _can_access(commission) or commission.payment_status in {
        "Paid",
        "Cancelled",
    }:
        flash("This commission cannot accept a payment.", "danger")
        return redirect(url_for("commissions.details", id=id))
    if request.method == "POST":
        amount = _decimal(request.form.get("amount"), positive=True)
        try:
            payment_date = datetime.strptime(
                request.form.get("payment_date", ""), "%Y-%m-%d"
            ).date()
        except ValueError:
            payment_date = None
        if not payment_date or amount is None:
            error = "Payment date and a positive amount are required."
        elif amount > Decimal(commission.balance):
            error = "Payment cannot exceed the outstanding balance."
        else:
            error = None
        if not error:
            db.session.add(
                CommissionPayment(
                    commission=commission,
                    payment_date=payment_date,
                    amount=amount.quantize(Decimal("0.01")),
                    reference_number=request.form.get("reference_number", "").strip()
                    or None,
                    notes=request.form.get("notes", "").strip() or None,
                )
            )
            db.session.flush()
            commission.recalculate()
            db.session.commit()
            flash("Commission payment recorded successfully.", "success")
            return redirect(url_for("commissions.details", id=id))
        flash(error, "danger")
    return render_template(
        "commissions/payment_form.html",
        commission=commission,
        today=date.today().isoformat(),
    )


@commissions.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    commission = PropertyCommission.query.get_or_404(id)
    if not _can_access(commission) or commission.payments:
        flash("Only unpaid commissions may be cancelled.", "danger")
    else:
        commission.payment_status = "Cancelled"
        db.session.commit()
        flash("Commission cancelled.", "success")
    return redirect(url_for("commissions.details", id=id))


@commissions.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    commission = PropertyCommission.query.get_or_404(id)
    if not _is_admin():
        flash("Only administrators can delete commissions.", "danger")
    else:
        db.session.delete(commission)
        db.session.commit()
        flash("Commission deleted successfully.", "success")
        return redirect(url_for("commissions.index"))
    return redirect(url_for("commissions.details", id=id))
