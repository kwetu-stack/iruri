from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import render_template, request
from sqlalchemy import case, func, or_
from sqlalchemy.orm import joinedload

from app.agents.models import Agent
from app.buyers.models import Buyer
from app.commissions.models import PropertyCommission
from app.extensions import db
from app.offers.models import PropertyOffer
from app.properties.models import Property, SavedProperty
from app.reports import reports
from app.reservations.models import PropertyReservation
from app.sale_agreements.models import PropertyPayment, SaleAgreement
from app.sellers.models import Seller
from app.transactions.models import PropertyTransaction
from app.utils.permissions import require_permission
from app.viewings.models import ViewingRequest


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


def _buyer_name():
    return func.coalesce(Buyer.full_name, Buyer.company_name, Buyer.buyer_number)


def _seller_name():
    return func.coalesce(Seller.full_name, Seller.company_name, Seller.seller_number)


def _apply_marketplace_filters(query, start_at, end_at):
    query = _apply_datetime_window(query, Property.created_at, start_at, end_at)
    property_type = request.args.get("property_type", "").strip()
    status = request.args.get("status", "").strip()
    seller_id = request.args.get("seller_id", "").strip()
    agent_id = request.args.get("agent_id", "").strip()
    search = request.args.get("q", "").strip()

    if property_type:
        query = query.filter(Property.property_type == property_type)
    if status:
        query = query.filter(Property.status == status)
    if seller_id.isdigit():
        query = query.filter(Property.seller_id == int(seller_id))
    if agent_id.isdigit():
        query = query.filter(Property.agent_id == int(agent_id))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Property.listing_number.ilike(pattern),
                Property.title.ilike(pattern),
                Seller.full_name.ilike(pattern),
                Seller.company_name.ilike(pattern),
                Agent.first_name.ilike(pattern),
                Agent.last_name.ilike(pattern),
            )
        )
    return query


def _percentage(count, total):
    return round((count / total) * 100, 1) if total else 0


def _pagination_args():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    return page, 25


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


@reports.route("/marketplace")
@reports.route("/marketplace/", strict_slashes=False)
@require_permission("reports.marketplace")
def marketplace_dashboard():
    selected_period, start_date, end_date = _date_window()
    start_at, end_at = _datetime_bounds(start_date, end_date)
    page, per_page = _pagination_args()

    base_query = Property.query.outerjoin(Seller).outerjoin(Agent)
    filtered_query = _apply_marketplace_filters(base_query, start_at, end_at)
    total_listings = filtered_query.count()

    status_rows = dict(
        filtered_query.with_entities(Property.status, func.count(Property.id))
        .group_by(Property.status)
        .all()
    )
    property_type_case = case(
        (Property.property_type.in_(PROPERTY_TYPE_LABELS[:-1]), Property.property_type),
        else_="Other",
    ).label("property_type")
    type_rows = {
        row.property_type: row
        for row in filtered_query.with_entities(
            property_type_case,
            func.count(Property.id).label("count"),
            func.coalesce(func.avg(Property.price), 0).label("average_price"),
        )
        .group_by(property_type_case)
        .all()
    }

    listings = (
        filtered_query.options(joinedload(Property.seller), joinedload(Property.agent))
        .order_by(Property.created_at.desc(), Property.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    completed_transactions = (
        PropertyTransaction.query.filter_by(transaction_status="Completed")
        .join(Property, Property.id == PropertyTransaction.property_id)
        .outerjoin(Seller, Seller.id == Property.seller_id)
        .outerjoin(Agent, Agent.id == Property.agent_id)
    )
    completed_transactions = _apply_marketplace_filters(
        completed_transactions, start_at, end_at
    )

    seller_rows = (
        filtered_query.with_entities(
            Seller.id,
            _seller_name().label("seller"),
            func.count(Property.id).label("listed"),
        )
        .group_by(Seller.id, Seller.full_name, Seller.company_name, Seller.seller_number)
        .subquery()
    )
    seller_sales = (
        completed_transactions.with_entities(
            Property.seller_id.label("seller_id"),
            func.count(PropertyTransaction.id).label("sold"),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label("revenue"),
        )
        .group_by(Property.seller_id)
        .subquery()
    )
    sellers_report = (
        db.session.query(
            seller_rows.c.seller,
            seller_rows.c.listed,
            func.coalesce(seller_sales.c.sold, 0).label("sold"),
            func.coalesce(seller_sales.c.revenue, 0).label("revenue"),
        )
        .outerjoin(seller_sales, seller_sales.c.seller_id == seller_rows.c.id)
        .order_by(func.coalesce(seller_sales.c.revenue, 0).desc(), seller_rows.c.listed.desc())
        .limit(20)
        .all()
    )

    commission_rows = (
        db.session.query(
            PropertyCommission.agent_id,
            func.coalesce(func.sum(PropertyCommission.commission_amount), 0).label("commission"),
        )
        .join(Property, Property.id == PropertyCommission.property_id)
        .outerjoin(Seller, Seller.id == Property.seller_id)
        .outerjoin(Agent, Agent.id == Property.agent_id)
    )
    commission_rows = _apply_marketplace_filters(commission_rows, start_at, end_at)
    commission_rows = commission_rows.group_by(PropertyCommission.agent_id).subquery()

    agent_rows = (
        filtered_query.with_entities(
            Agent.id,
            Agent.first_name,
            Agent.last_name,
            func.count(Property.id).label("managed"),
        )
        .filter(Property.agent_id.isnot(None))
        .group_by(Agent.id, Agent.first_name, Agent.last_name)
        .subquery()
    )
    agent_sales = (
        completed_transactions.with_entities(
            Property.agent_id.label("agent_id"),
            func.count(PropertyTransaction.id).label("sales"),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label("revenue"),
        )
        .filter(Property.agent_id.isnot(None))
        .group_by(Property.agent_id)
        .subquery()
    )
    agents_report = (
        db.session.query(
            agent_rows.c.first_name,
            agent_rows.c.last_name,
            agent_rows.c.managed,
            func.coalesce(agent_sales.c.sales, 0).label("sales"),
            func.coalesce(agent_sales.c.revenue, 0).label("revenue"),
            func.coalesce(commission_rows.c.commission, 0).label("commission"),
        )
        .outerjoin(agent_sales, agent_sales.c.agent_id == agent_rows.c.id)
        .outerjoin(commission_rows, commission_rows.c.agent_id == agent_rows.c.id)
        .order_by(func.coalesce(agent_sales.c.sales, 0).desc(), func.coalesce(agent_sales.c.revenue, 0).desc())
        .limit(20)
        .all()
    )

    buyer_interest = (
        db.session.query(
            _buyer_name().label("buyer"),
            func.count(func.distinct(SavedProperty.id)).label("saved_properties"),
            func.count(func.distinct(ViewingRequest.id)).label("viewing_requests"),
            func.count(func.distinct(PropertyOffer.id)).label("offers_submitted"),
            func.count(func.distinct(PropertyReservation.id)).label("reservations"),
        )
        .select_from(Buyer)
        .outerjoin(SavedProperty, SavedProperty.buyer_id == Buyer.id)
        .outerjoin(ViewingRequest, ViewingRequest.buyer_id == Buyer.id)
        .outerjoin(PropertyOffer, PropertyOffer.buyer_id == Buyer.id)
        .outerjoin(PropertyReservation, PropertyReservation.buyer_id == Buyer.id)
        .group_by(Buyer.id, Buyer.full_name, Buyer.company_name, Buyer.buyer_number)
        .order_by(func.count(func.distinct(PropertyOffer.id)).desc(), func.count(func.distinct(ViewingRequest.id)).desc())
        .limit(20)
        .all()
    )

    monthly_rows = (
        filtered_query.with_entities(
            func.extract("year", Property.created_at).label("year"),
            func.extract("month", Property.created_at).label("month"),
            func.count(Property.id).label("count"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    statuses = ("Available", "Reserved", "Sold", "Inactive")
    status_report = [
        {"label": label, "count": status_rows.get(label, 0), "percentage": _percentage(status_rows.get(label, 0), total_listings)}
        for label in statuses
    ]
    type_report = [
        {
            "label": label,
            "count": type_rows.get(label).count if label in type_rows else 0,
            "percentage": _percentage(type_rows.get(label).count if label in type_rows else 0, total_listings),
            "average_price": type_rows.get(label).average_price if label in type_rows else 0,
        }
        for label in PROPERTY_TYPE_LABELS
    ]
    summary = {
        "total_listings": total_listings,
        "active_listings": status_rows.get("Available", 0),
        "sold_listings": status_rows.get("Sold", 0),
        "reserved_listings": status_rows.get("Reserved", 0),
    }
    chart_data = {
        "property_status": {"labels": list(statuses), "values": [status_rows.get(label, 0) for label in statuses]},
        "property_types": {"labels": list(PROPERTY_TYPE_LABELS), "values": [item["count"] for item in type_report]},
        "monthly_listings": {"labels": [_month_label(int(row.year), int(row.month)) for row in monthly_rows if row.year and row.month], "values": [row.count for row in monthly_rows if row.year and row.month]},
        "agent_performance": {"labels": [f"{row.first_name} {row.last_name}" for row in agents_report[:10]], "values": [row.sales for row in agents_report[:10]]},
        "seller_performance": {"labels": [row.seller for row in sellers_report[:10]], "values": [float(row.revenue) for row in sellers_report[:10]]},
    }

    return render_template(
        "reports/marketplace.html",
        selected_period=selected_period,
        date_from=start_date.isoformat() if start_date else "",
        date_to=end_date.isoformat() if end_date else "",
        filters=request.args,
        filter_params={key: value for key, value in request.args.items() if key != "page"},
        property_types=PROPERTY_TYPE_LABELS,
        statuses=statuses,
        sellers=Seller.query.order_by(Seller.full_name, Seller.company_name).all(),
        agents=Agent.query.order_by(Agent.first_name, Agent.last_name).all(),
        listings=listings,
        summary=summary,
        status_report=status_report,
        type_report=type_report,
        sellers_report=sellers_report,
        agents_report=agents_report,
        buyer_interest=buyer_interest,
        chart_data=chart_data,
    )
