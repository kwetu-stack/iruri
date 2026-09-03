from datetime import date, datetime
from decimal import Decimal

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.commissions.models import PropertyCommission
from app.buyers.models import Buyer
from app.extensions import db
from app.properties.models import Property
from app.sale_agreements.models import SaleAgreement
from app.sellers.models import Seller
from app.transactions import transactions
from app.transactions.models import PropertyTransaction


def _is_admin():
    return (current_user.role or "").lower() in {"admin", "administrator"}


def _can_access(transaction):
    if _is_admin():
        return True
    email = (current_user.email or "").lower()
    return bool(email) and email in {
        (transaction.buyer.email or "").lower(),
        (transaction.seller.email or "").lower(),
        (
            (transaction.property.agent.email or "").lower()
            if transaction.property.agent
            else ""
        ),
    }


def _parse_date(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except (AttributeError, ValueError):
        return None


def _completion_error(agreement, completion_date, transfer_date):
    if agreement.status != "Completed":
        return "The sale agreement must be completed first."
    if agreement.outstanding_balance != Decimal("0.00"):
        return "The outstanding payment balance must be zero."
    if any(item.payment_status != "Paid" for item in agreement.commissions):
        return "All commissions must be fully paid."
    if PropertyTransaction.query.filter_by(
        property_id=agreement.property_id, transaction_status="Completed"
    ).first():
        return "This property already has a completed transaction."
    if not completion_date:
        return "Completion date is required."
    if completion_date < agreement.agreement_date:
        return "Completion date cannot precede the agreement date."
    if transfer_date and transfer_date < completion_date:
        return "Transfer date cannot precede the completion date."
    return None


def _form_context(agreement):
    return {
        "agreement": agreement,
        "today": date.today().isoformat(),
        "transaction": None,
    }


@transactions.route("/")
@login_required
def index():
    query = PropertyTransaction.query.filter_by(transaction_status="Completed")
    search = request.args.get("q", "").strip()
    if search:
        pattern = f"%{search}%"
        query = (
            query.join(PropertyTransaction.property)
            .join(PropertyTransaction.buyer)
            .join(PropertyTransaction.seller)
            .filter(
                db.or_(
                    PropertyTransaction.transaction_number.ilike(pattern),
                    Property.title.ilike(pattern),
                    Buyer.full_name.ilike(pattern),
                    Buyer.company_name.ilike(pattern),
                    Seller.full_name.ilike(pattern),
                    Seller.company_name.ilike(pattern),
                )
            )
        )
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    if start_date:
        query = query.filter(PropertyTransaction.completion_date >= start_date)
    if end_date:
        query = query.filter(PropertyTransaction.completion_date <= end_date)
    all_transactions = [
        item
        for item in query.order_by(PropertyTransaction.completion_date.desc()).all()
        if _can_access(item)
    ]
    now = date.today()
    this_month = sum(
        item.completion_date.year == now.year
        and item.completion_date.month == now.month
        for item in all_transactions
    )
    this_year = sum(item.completion_date.year == now.year for item in all_transactions)
    total_value = sum(
        (Decimal(item.final_sale_price) for item in all_transactions), Decimal("0.00")
    )
    return render_template(
        "transactions/index.html",
        transactions=all_transactions,
        search=search,
        start_date=request.args.get("start_date", ""),
        end_date=request.args.get("end_date", ""),
        total_completed=len(all_transactions),
        total_sales_value=total_value,
        average_sale_price=(
            total_value / len(all_transactions) if all_transactions else Decimal("0.00")
        ),
        transactions_this_month=this_month,
        transactions_this_year=this_year,
    )


@transactions.route("/<int:id>")
@login_required
def details(id):
    transaction = PropertyTransaction.query.get_or_404(id)
    if not _can_access(transaction):
        flash("You are not authorized to view this transaction.", "danger")
        return redirect(url_for("transactions.index"))
    return render_template("transactions/details.html", transaction=transaction)


@transactions.route("/complete/<int:agreement_id>", methods=["GET", "POST"])
@login_required
def complete(agreement_id):
    agreement = SaleAgreement.query.get_or_404(agreement_id)
    if not _is_admin() and not any(
        (current_user.email or "").lower() == (value or "").lower()
        for value in (
            agreement.buyer.email,
            agreement.seller.email,
            agreement.property.agent.email if agreement.property.agent else None,
        )
    ):
        flash("You are not authorized to complete this transaction.", "danger")
        return redirect(url_for("sale_agreements.details", id=agreement.id))
    existing = PropertyTransaction.query.filter_by(
        sale_agreement_id=agreement.id
    ).first()
    if existing:
        return redirect(url_for("transactions.details", id=existing.id))
    if request.method == "POST":
        completion_date = _parse_date(request.form.get("completion_date"))
        transfer_date = _parse_date(request.form.get("transfer_date"))
        error = _completion_error(agreement, completion_date, transfer_date)
        if not error:
            transaction = PropertyTransaction(
                transaction_number="TEMP",
                sale_agreement=agreement,
                property=agreement.property,
                buyer=agreement.buyer,
                seller=agreement.seller,
                completion_date=completion_date,
                transfer_date=transfer_date,
                final_sale_price=agreement.agreed_price,
                currency=agreement.currency,
                transaction_status="Completed",
                completed_by=current_user.email or current_user.get_id(),
                notes=request.form.get("notes", "").strip() or None,
            )
            db.session.add(transaction)
            agreement.property.status = "Sold"
            agreement.reservation.status = "Completed"
            db.session.flush()
            transaction.transaction_number = (
                f"TRX-{datetime.utcnow().year}-{transaction.id:06d}"
            )
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                error = "This property already has a completed transaction."
            else:
                flash("Transaction completed successfully.", "success")
                return redirect(url_for("transactions.details", id=transaction.id))
        flash(error, "danger")
    return render_template("transactions/form.html", **_form_context(agreement))
