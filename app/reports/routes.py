from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import render_template, request
from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

from app.agents.models import Agent
from app.buyers.models import Buyer
from app.commissions.models import PropertyCommission
from app.extensions import db
from app.properties.models import Property
from app.reports import reports
from app.reservations.models import PropertyReservation
from app.sale_agreements.models import PropertyPayment, SaleAgreement
from app.sellers.models import Seller
from app.transactions.models import PropertyTransaction
from app.utils.permissions import require_permission


FILTER_OPTIONS = ("today", "week", "month", "year", "custom")
PROPERTY_TYPE_LABELS = ("Apartment", "House", "Villa", "Land", "Commercial", "Other")


def _date_window():
    selected = request.args.get("period", "month").strip()
    if selected not in FILTER_OPTIONS:
        selected = "month"

    today = date.today()
    start_date = None
    end_date = today

    if selected == "today":
        start_date = today
    elif selected == "week":
        start_date = today - timedelta(days=today.weekday())
    elif selected == "month":
        start_date = today.replace(day=1)
    elif selected == "year":
        start_date = today.replace(month=1, day=1)
    elif selected == "custom":
        start_raw = request.args.get("date_from", "").strip()
        end_raw = request.args.get("date_to", "").strip()
        try:
            start_date = datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else None
            end_date = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else today
        except ValueError:
            selected = "month"
            start_date = today.replace(day=1)
            end_date = today

    return selected, start_date, end_date


def _datetime_bounds(start_date, end_date):
    start_at = datetime.combine(start_date, time.min) if start_date else None
    end_at = datetime.combine(end_date, time.max) if end_date else None
    return start_at, end_at


def _apply_datetime_window(query, column, start_at, end_at):
    if start_at:
        query = query.filter(column >= start_at)
    if end_at:
        query = query.filter(column <= end_at)
    return query


def _apply_date_window(query, column, start_date, end_date):
    if start_date:
        query = query.filter(column >= start_date)
    if end_date:
        query = query.filter(column <= end_date)
    return query


def _money(value):
    return value or Decimal("0.00")


def _month_label(year, month):
    return date(year, month, 1).strftime("%b %Y")


@reports.route("/executive")
@reports.route("/executive/", strict_slashes=False)
@require_permission("reports.executive")
def executive_dashboard():
    selected_period, start_date, end_date = _date_window()
    start_at, end_at = _datetime_bounds(start_date, end_date)

    property_query = _apply_datetime_window(Property.query, Property.created_at, start_at, end_at)
    reservation_query = _apply_datetime_window(
        PropertyReservation.query, PropertyReservation.created_at, start_at, end_at
    )
    transaction_query = _apply_datetime_window(
        PropertyTransaction.query, PropertyTransaction.created_at, start_at, end_at
    )
    completed_transaction_query = _apply_date_window(
        PropertyTransaction.query.filter_by(transaction_status="Completed"),
        PropertyTransaction.completion_date,
        start_date,
        end_date,
    )
    payment_query = _apply_date_window(
        PropertyPayment.query, PropertyPayment.payment_date, start_date, end_date
    )
    commission_query = _apply_datetime_window(
        PropertyCommission.query, PropertyCommission.created_at, start_at, end_at
    )

    property_status_counts = dict(
        property_query.with_entities(Property.status, func.count(Property.id))
        .group_by(Property.status)
        .all()
    )
    property_type_counts = dict(
        property_query.with_entities(
            case(
                (Property.property_type.in_(PROPERTY_TYPE_LABELS[:-1]), Property.property_type),
                else_="Other",
            ).label("property_type"),
            func.count(Property.id),
        )
        .group_by("property_type")
        .all()
    )

    monthly_sales_rows = (
        completed_transaction_query.with_entities(
            func.extract("year", PropertyTransaction.completion_date).label("year"),
            func.extract("month", PropertyTransaction.completion_date).label("month"),
            func.count(PropertyTransaction.id),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )
    month_labels = [_month_label(int(row[0]), int(row[1])) for row in monthly_sales_rows]

    total_revenue = _money(
        completed_transaction_query.with_entities(
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    total_commission = _money(
        commission_query.with_entities(
            func.coalesce(func.sum(PropertyCommission.commission_amount), 0)
        ).scalar()
    )

    top_agents = (
        completed_transaction_query.join(Property, Property.id == PropertyTransaction.property_id)
        .join(Agent, Agent.id == Property.agent_id)
        .with_entities(
            Agent.id,
            Agent.first_name,
            Agent.last_name,
            func.count(PropertyTransaction.id).label("completed_sales"),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label("revenue"),
        )
        .group_by(Agent.id, Agent.first_name, Agent.last_name)
        .order_by(func.count(PropertyTransaction.id).desc(), func.sum(PropertyTransaction.final_sale_price).desc())
        .limit(10)
        .all()
    )

    latest_transactions = (
        transaction_query.options(
            joinedload(PropertyTransaction.property),
            joinedload(PropertyTransaction.buyer),
        )
        .order_by(PropertyTransaction.created_at.desc(), PropertyTransaction.id.desc())
        .limit(10)
        .all()
    )
    paid_subquery = (
        payment_query.with_entities(
            PropertyPayment.sale_agreement_id,
            func.coalesce(func.sum(PropertyPayment.amount), 0).label("paid_amount"),
        )
        .filter(PropertyPayment.payment_type != "Refund")
        .group_by(PropertyPayment.sale_agreement_id)
        .subquery()
    )
    pending_payments = (
        _apply_datetime_window(SaleAgreement.query, SaleAgreement.created_at, start_at, end_at)
        .outerjoin(paid_subquery, paid_subquery.c.sale_agreement_id == SaleAgreement.id)
        .filter(func.coalesce(paid_subquery.c.paid_amount, 0) < SaleAgreement.agreed_price)
        .count()
    )

    kpis = {
        "total_properties": property_query.count(),
        "available_properties": property_status_counts.get("Available", 0),
        "reserved_properties": property_status_counts.get("Reserved", 0),
        "sold_properties": property_status_counts.get("Sold", 0),
        "total_buyers": _apply_datetime_window(Buyer.query, Buyer.created_at, start_at, end_at).count(),
        "active_buyers": _apply_datetime_window(Buyer.query.filter_by(active=True), Buyer.created_at, start_at, end_at).count(),
        "total_sellers": _apply_datetime_window(Seller.query, Seller.created_at, start_at, end_at).count(),
        "total_agents": _apply_datetime_window(Agent.query, Agent.created_at, start_at, end_at).count(),
        "total_transactions": transaction_query.count(),
        "total_reservations": reservation_query.count(),
        "total_revenue": total_revenue,
        "total_commission": total_commission,
    }
    summary = {
        "total_revenue": total_revenue,
        "outstanding_reservations": PropertyReservation.query.filter(
            PropertyReservation.status.in_(("Pending", "Active"))
        ).count(),
        "pending_payments": pending_payments,
        "active_listings": Property.query.filter_by(status="Available").count(),
        "average_property_price": _money(
            property_query.with_entities(func.coalesce(func.avg(Property.price), 0)).scalar()
        ),
    }
    chart_data = {
        "property_status": {
            "labels": ["Available", "Reserved", "Sold"],
            "values": [
                property_status_counts.get("Available", 0),
                property_status_counts.get("Reserved", 0),
                property_status_counts.get("Sold", 0),
            ],
        },
        "monthly_sales": {
            "labels": month_labels,
            "values": [int(row[2]) for row in monthly_sales_rows],
        },
        "revenue_trend": {
            "labels": month_labels,
            "values": [float(row[3]) for row in monthly_sales_rows],
        },
        "property_types": {
            "labels": list(PROPERTY_TYPE_LABELS),
            "values": [property_type_counts.get(label, 0) for label in PROPERTY_TYPE_LABELS],
        },
    }

    return render_template(
        "reports/executive.html",
        kpis=kpis,
        summary=summary,
        chart_data=chart_data,
        top_agents=top_agents,
        latest_transactions=latest_transactions,
        selected_period=selected_period,
        date_from=start_date.isoformat() if start_date else "",
        date_to=end_date.isoformat() if end_date else "",
    )
