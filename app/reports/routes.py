from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import abort, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import case, func, or_
from sqlalchemy.orm import joinedload

from app.agents.models import Agent
from app.activities.models import ActivityLog
from app.admin.email_templates import EMAIL_TEMPLATE_CATEGORIES, EmailTemplate
from app.admin.models import SystemBackup
from app.admin.roles import Permission, Role
from app.audit.models import AuditLog
from app.audit.service import record_audit
from app.notifications.models import Notification
from app.auth.models import User
from app.buyers.models import Buyer
from app.commissions.models import PropertyCommission
from app.extensions import db
from app.offers.models import PropertyOffer
from app.properties.models import Property, SavedProperty
from app.reports import reports
from app.reservations.models import PropertyReservation
from app.sale_agreements.models import PropertyPayment, SaleAgreement
from app.sellers.models import Seller
from app.transactions.models import TRANSACTION_STATUSES, PropertyTransaction
from app.utils.permissions import require_permission
from app.viewings.models import ViewingRequest
from app.reports.export_service import build_report_response

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
            start_date = (
                datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else None
            )
            end_date = (
                datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else today
            )
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

    property_query = _apply_datetime_window(
        Property.query, Property.created_at, start_at, end_at
    )
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
                (
                    Property.property_type.in_(PROPERTY_TYPE_LABELS[:-1]),
                    Property.property_type,
                ),
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
    month_labels = [
        _month_label(int(row[0]), int(row[1])) for row in monthly_sales_rows
    ]

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
        completed_transaction_query.join(
            Property, Property.id == PropertyTransaction.property_id
        )
        .join(Agent, Agent.id == Property.agent_id)
        .with_entities(
            Agent.id,
            Agent.first_name,
            Agent.last_name,
            func.count(PropertyTransaction.id).label("completed_sales"),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label(
                "revenue"
            ),
        )
        .group_by(Agent.id, Agent.first_name, Agent.last_name)
        .order_by(
            func.count(PropertyTransaction.id).desc(),
            func.sum(PropertyTransaction.final_sale_price).desc(),
        )
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
        _apply_datetime_window(
            SaleAgreement.query, SaleAgreement.created_at, start_at, end_at
        )
        .outerjoin(paid_subquery, paid_subquery.c.sale_agreement_id == SaleAgreement.id)
        .filter(
            func.coalesce(paid_subquery.c.paid_amount, 0) < SaleAgreement.agreed_price
        )
        .count()
    )

    kpis = {
        "total_properties": property_query.count(),
        "available_properties": property_status_counts.get("Available", 0),
        "reserved_properties": property_status_counts.get("Reserved", 0),
        "sold_properties": property_status_counts.get("Sold", 0),
        "total_buyers": _apply_datetime_window(
            Buyer.query, Buyer.created_at, start_at, end_at
        ).count(),
        "active_buyers": _apply_datetime_window(
            Buyer.query.filter_by(active=True), Buyer.created_at, start_at, end_at
        ).count(),
        "total_sellers": _apply_datetime_window(
            Seller.query, Seller.created_at, start_at, end_at
        ).count(),
        "total_agents": _apply_datetime_window(
            Agent.query, Agent.created_at, start_at, end_at
        ).count(),
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
            property_query.with_entities(
                func.coalesce(func.avg(Property.price), 0)
            ).scalar()
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
            "values": [
                property_type_counts.get(label, 0) for label in PROPERTY_TYPE_LABELS
            ],
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
        .group_by(
            Seller.id, Seller.full_name, Seller.company_name, Seller.seller_number
        )
        .subquery()
    )
    seller_sales = (
        completed_transactions.with_entities(
            Property.seller_id.label("seller_id"),
            func.count(PropertyTransaction.id).label("sold"),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label(
                "revenue"
            ),
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
        .order_by(
            func.coalesce(seller_sales.c.revenue, 0).desc(), seller_rows.c.listed.desc()
        )
        .limit(20)
        .all()
    )

    commission_rows = (
        db.session.query(
            PropertyCommission.agent_id,
            func.coalesce(func.sum(PropertyCommission.commission_amount), 0).label(
                "commission"
            ),
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
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label(
                "revenue"
            ),
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
        .order_by(
            func.coalesce(agent_sales.c.sales, 0).desc(),
            func.coalesce(agent_sales.c.revenue, 0).desc(),
        )
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
        .order_by(
            func.count(func.distinct(PropertyOffer.id)).desc(),
            func.count(func.distinct(ViewingRequest.id)).desc(),
        )
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
        {
            "label": label,
            "count": status_rows.get(label, 0),
            "percentage": _percentage(status_rows.get(label, 0), total_listings),
        }
        for label in statuses
    ]
    type_report = [
        {
            "label": label,
            "count": type_rows.get(label).count if label in type_rows else 0,
            "percentage": _percentage(
                type_rows.get(label).count if label in type_rows else 0, total_listings
            ),
            "average_price": (
                type_rows.get(label).average_price if label in type_rows else 0
            ),
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
        "property_status": {
            "labels": list(statuses),
            "values": [status_rows.get(label, 0) for label in statuses],
        },
        "property_types": {
            "labels": list(PROPERTY_TYPE_LABELS),
            "values": [item["count"] for item in type_report],
        },
        "monthly_listings": {
            "labels": [
                _month_label(int(row.year), int(row.month))
                for row in monthly_rows
                if row.year and row.month
            ],
            "values": [row.count for row in monthly_rows if row.year and row.month],
        },
        "agent_performance": {
            "labels": [
                f"{row.first_name} {row.last_name}" for row in agents_report[:10]
            ],
            "values": [row.sales for row in agents_report[:10]],
        },
        "seller_performance": {
            "labels": [row.seller for row in sellers_report[:10]],
            "values": [float(row.revenue) for row in sellers_report[:10]],
        },
    }

    return render_template(
        "reports/marketplace.html",
        selected_period=selected_period,
        date_from=start_date.isoformat() if start_date else "",
        date_to=end_date.isoformat() if end_date else "",
        filters=request.args,
        filter_params={
            key: value for key, value in request.args.items() if key != "page"
        },
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


@reports.route("/transactions")
@reports.route("/transactions/", strict_slashes=False)
@require_permission("reports.transactions")
def transactions_dashboard():
    selected_period, start_date, end_date = _date_window()
    page, per_page = _pagination_args()

    transaction_query = (
        PropertyTransaction.query.join(
            Property, Property.id == PropertyTransaction.property_id
        )
        .outerjoin(Buyer, Buyer.id == PropertyTransaction.buyer_id)
        .outerjoin(Seller, Seller.id == PropertyTransaction.seller_id)
    )
    transaction_query = _apply_date_window(
        transaction_query, PropertyTransaction.completion_date, start_date, end_date
    )

    status = request.args.get("status", "").strip()
    seller_id = request.args.get("seller_id", "").strip()
    agent_id = request.args.get("agent_id", "").strip()
    search = request.args.get("q", "").strip()
    if status in TRANSACTION_STATUSES:
        transaction_query = transaction_query.filter(
            PropertyTransaction.transaction_status == status
        )
    if seller_id.isdigit():
        transaction_query = transaction_query.filter(
            PropertyTransaction.seller_id == int(seller_id)
        )
    if agent_id.isdigit():
        transaction_query = transaction_query.filter(Property.agent_id == int(agent_id))
    if search:
        pattern = f"%{search}%"
        transaction_query = transaction_query.filter(
            or_(
                PropertyTransaction.transaction_number.ilike(pattern),
                Property.listing_number.ilike(pattern),
                Property.title.ilike(pattern),
                Buyer.full_name.ilike(pattern),
                Buyer.company_name.ilike(pattern),
                Seller.full_name.ilike(pattern),
                Seller.company_name.ilike(pattern),
            )
        )

    payment_totals = (
        PropertyPayment.query.with_entities(
            PropertyPayment.sale_agreement_id,
            func.coalesce(
                func.sum(
                    case(
                        (
                            PropertyPayment.payment_type == "Refund",
                            -PropertyPayment.amount,
                        ),
                        else_=PropertyPayment.amount,
                    )
                ),
                0,
            ).label("paid"),
        )
        .group_by(PropertyPayment.sale_agreement_id)
        .subquery()
    )
    commission_totals = (
        PropertyCommission.query.with_entities(
            PropertyCommission.sale_agreement_id,
            func.coalesce(func.sum(PropertyCommission.commission_amount), 0).label(
                "generated"
            ),
            func.coalesce(func.sum(PropertyCommission.amount_paid), 0).label(
                "commission_paid"
            ),
            func.coalesce(func.sum(PropertyCommission.balance), 0).label(
                "commission_balance"
            ),
        )
        .group_by(PropertyCommission.sale_agreement_id)
        .subquery()
    )
    financial_query = transaction_query.outerjoin(
        payment_totals,
        payment_totals.c.sale_agreement_id == PropertyTransaction.sale_agreement_id,
    ).outerjoin(
        commission_totals,
        commission_totals.c.sale_agreement_id == PropertyTransaction.sale_agreement_id,
    )
    total_transactions = transaction_query.count()
    status_counts = dict(
        transaction_query.with_entities(
            PropertyTransaction.transaction_status, func.count(PropertyTransaction.id)
        )
        .group_by(PropertyTransaction.transaction_status)
        .all()
    )
    completed_query = transaction_query.filter(
        PropertyTransaction.transaction_status == "Completed"
    )
    completed_value = _money(
        completed_query.with_entities(
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    average_completed_value = _money(
        completed_query.with_entities(
            func.coalesce(func.avg(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    financial_totals = (
        financial_query.with_entities(
            func.coalesce(func.sum(payment_totals.c.paid), 0),
            func.coalesce(
                func.sum(
                    SaleAgreement.agreed_price - func.coalesce(payment_totals.c.paid, 0)
                ),
                0,
            ),
            func.coalesce(func.sum(commission_totals.c.generated), 0),
            func.coalesce(func.sum(commission_totals.c.commission_paid), 0),
            func.coalesce(func.sum(commission_totals.c.commission_balance), 0),
        )
        .join(SaleAgreement, SaleAgreement.id == PropertyTransaction.sale_agreement_id)
        .first()
    )

    transactions = (
        transaction_query.options(
            joinedload(PropertyTransaction.property),
            joinedload(PropertyTransaction.buyer),
            joinedload(PropertyTransaction.seller),
            joinedload(PropertyTransaction.sale_agreement),
        )
        .order_by(
            PropertyTransaction.completion_date.desc(), PropertyTransaction.id.desc()
        )
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    monthly_rows = (
        completed_query.with_entities(
            func.extract("year", PropertyTransaction.completion_date).label("year"),
            func.extract("month", PropertyTransaction.completion_date).label("month"),
            func.count(PropertyTransaction.id).label("count"),
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0).label(
                "value"
            ),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )
    filter_params = {key: value for key, value in request.args.items() if key != "page"}
    summary = {
        "total_transactions": total_transactions,
        "completed_transactions": status_counts.get("Completed", 0),
        "pending_transactions": status_counts.get("Pending Completion", 0),
        "cancelled_transactions": status_counts.get("Cancelled", 0),
        "completed_value": completed_value,
        "average_completed_value": average_completed_value,
        "payments_received": _money(financial_totals[0]),
        "payments_outstanding": _money(financial_totals[1]),
        "commission_generated": _money(financial_totals[2]),
        "commission_paid": _money(financial_totals[3]),
        "commission_outstanding": _money(financial_totals[4]),
    }
    chart_data = {
        "status": {
            "labels": list(TRANSACTION_STATUSES),
            "values": [status_counts.get(label, 0) for label in TRANSACTION_STATUSES],
        },
        "monthly_sales": {
            "labels": [
                _month_label(int(row.year), int(row.month)) for row in monthly_rows
            ],
            "values": [row.count for row in monthly_rows],
        },
        "monthly_value": {
            "labels": [
                _month_label(int(row.year), int(row.month)) for row in monthly_rows
            ],
            "values": [float(row.value) for row in monthly_rows],
        },
    }
    return render_template(
        "reports/transactions.html",
        selected_period=selected_period,
        date_from=start_date.isoformat() if start_date else "",
        date_to=end_date.isoformat() if end_date else "",
        filters=request.args,
        filter_params=filter_params,
        statuses=TRANSACTION_STATUSES,
        sellers=Seller.query.order_by(Seller.full_name, Seller.company_name).all(),
        agents=Agent.query.order_by(Agent.first_name, Agent.last_name).all(),
        transactions=transactions,
        summary=summary,
        chart_data=chart_data,
    )


@reports.route("/financial")
@reports.route("/financial/", strict_slashes=False)
@require_permission("reports.financial")
def financial_dashboard():
    selected_period, start_date, end_date = _date_window()
    page, per_page = _pagination_args()
    property_type = request.args.get("property_type", "").strip()
    status = request.args.get("status", "").strip()
    payment_status = request.args.get("payment_status", "").strip()
    payment_method = request.args.get("payment_method", "").strip()
    agent_id = request.args.get("agent_id", "").strip()
    search = request.args.get("q", "").strip()

    def apply_filters(query, date_column):
        query = _apply_date_window(query, date_column, start_date, end_date)
        if property_type:
            query = query.filter(Property.property_type == property_type)
        if status in TRANSACTION_STATUSES:
            query = query.filter(PropertyTransaction.transaction_status == status)
        if agent_id.isdigit():
            query = query.filter(Property.agent_id == int(agent_id))
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    PropertyTransaction.transaction_number.ilike(pattern),
                    Property.listing_number.ilike(pattern),
                    Property.title.ilike(pattern),
                    Buyer.full_name.ilike(pattern),
                    Buyer.company_name.ilike(pattern),
                    Seller.full_name.ilike(pattern),
                    Seller.company_name.ilike(pattern),
                    Agent.first_name.ilike(pattern),
                    Agent.last_name.ilike(pattern),
                )
            )
        return query

    transaction_query = (
        PropertyTransaction.query.join(
            Property, Property.id == PropertyTransaction.property_id
        )
        .outerjoin(Buyer, Buyer.id == PropertyTransaction.buyer_id)
        .outerjoin(Seller, Seller.id == PropertyTransaction.seller_id)
        .outerjoin(Agent, Agent.id == Property.agent_id)
    )
    transaction_query = apply_filters(
        transaction_query, PropertyTransaction.completion_date
    )
    payment_totals = (
        PropertyPayment.query.with_entities(
            PropertyPayment.sale_agreement_id,
            func.coalesce(
                func.sum(
                    case(
                        (
                            PropertyPayment.payment_type == "Refund",
                            -PropertyPayment.amount,
                        ),
                        else_=PropertyPayment.amount,
                    )
                ),
                0,
            ).label("paid"),
        )
        .group_by(PropertyPayment.sale_agreement_id)
        .subquery()
    )
    completed_transactions = transaction_query.filter(
        PropertyTransaction.transaction_status == "Completed"
    )
    total_revenue = _money(
        completed_transactions.with_entities(
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    average_sale_value = _money(
        completed_transactions.with_entities(
            func.coalesce(func.avg(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    highest_sale = _money(
        completed_transactions.with_entities(
            func.coalesce(func.max(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    lowest_sale = _money(
        completed_transactions.with_entities(
            func.coalesce(func.min(PropertyTransaction.final_sale_price), 0)
        ).scalar()
    )
    month_start = date.today().replace(day=1)
    year_start = date.today().replace(month=1, day=1)
    revenue_this_month = _money(
        completed_transactions.filter(
            PropertyTransaction.completion_date >= month_start
        )
        .with_entities(func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0))
        .scalar()
    )
    revenue_this_year = _money(
        completed_transactions.filter(PropertyTransaction.completion_date >= year_start)
        .with_entities(func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0))
        .scalar()
    )

    payment_query = (
        PropertyPayment.query.join(
            SaleAgreement, SaleAgreement.id == PropertyPayment.sale_agreement_id
        )
        .outerjoin(
            PropertyTransaction,
            PropertyTransaction.sale_agreement_id == SaleAgreement.id,
        )
        .join(Property, Property.id == SaleAgreement.property_id)
        .outerjoin(Buyer, Buyer.id == SaleAgreement.buyer_id)
        .outerjoin(Seller, Seller.id == SaleAgreement.seller_id)
        .outerjoin(Agent, Agent.id == Property.agent_id)
    )
    payment_query = apply_filters(payment_query, PropertyPayment.payment_date)
    if payment_status in ("Received", "Refund"):
        if payment_status == "Refund":
            payment_query = payment_query.filter(
                PropertyPayment.payment_type == "Refund"
            )
        else:
            payment_query = payment_query.filter(
                PropertyPayment.payment_type != "Refund"
            )
    if payment_method:
        if payment_method == "Other":
            payment_query = payment_query.filter(
                PropertyPayment.payment_method.notin_(
                    ("Cash", "Bank Transfer", "Mobile Money", "Cheque")
                )
            )
        else:
            payment_query = payment_query.filter(
                PropertyPayment.payment_method == payment_method
            )
    total_payments_received = _money(
        payment_query.filter(PropertyPayment.payment_type != "Refund")
        .with_entities(func.coalesce(func.sum(PropertyPayment.amount), 0))
        .scalar()
    )
    payments_this_month = _money(
        payment_query.filter(
            PropertyPayment.payment_type != "Refund",
            PropertyPayment.payment_date >= month_start,
        )
        .with_entities(func.coalesce(func.sum(PropertyPayment.amount), 0))
        .scalar()
    )
    payments_this_year = _money(
        payment_query.filter(
            PropertyPayment.payment_type != "Refund",
            PropertyPayment.payment_date >= year_start,
        )
        .with_entities(func.coalesce(func.sum(PropertyPayment.amount), 0))
        .scalar()
    )
    payments = (
        payment_query.options(
            joinedload(PropertyPayment.sale_agreement).joinedload(
                SaleAgreement.transactions
            ),
            joinedload(PropertyPayment.sale_agreement).joinedload(SaleAgreement.buyer),
        )
        .order_by(PropertyPayment.payment_date.desc(), PropertyPayment.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    outstanding_query = (
        SaleAgreement.query.join(Property, Property.id == SaleAgreement.property_id)
        .outerjoin(
            PropertyTransaction,
            PropertyTransaction.sale_agreement_id == SaleAgreement.id,
        )
        .outerjoin(Buyer, Buyer.id == SaleAgreement.buyer_id)
        .outerjoin(Seller, Seller.id == SaleAgreement.seller_id)
        .outerjoin(Agent, Agent.id == Property.agent_id)
        .outerjoin(
            payment_totals, payment_totals.c.sale_agreement_id == SaleAgreement.id
        )
    )
    outstanding_query = apply_filters(outstanding_query, SaleAgreement.completion_date)
    outstanding_query = outstanding_query.filter(
        SaleAgreement.agreed_price > func.coalesce(payment_totals.c.paid, 0)
    )
    outstanding = (
        outstanding_query.options(
            joinedload(SaleAgreement.payments),
            joinedload(SaleAgreement.property),
            joinedload(SaleAgreement.buyer),
        )
        .order_by(SaleAgreement.completion_date)
        .all()
    )
    outstanding_balance = _money(
        outstanding_query.with_entities(
            func.coalesce(
                func.sum(
                    SaleAgreement.agreed_price - func.coalesce(payment_totals.c.paid, 0)
                ),
                0,
            )
        ).scalar()
    )
    pending_payments = len(outstanding)

    commission_query = (
        PropertyCommission.query.join(Agent, Agent.id == PropertyCommission.agent_id)
        .join(Property, Property.id == PropertyCommission.property_id)
        .outerjoin(
            PropertyTransaction,
            PropertyTransaction.property_id == PropertyCommission.property_id,
        )
        .outerjoin(Buyer, Buyer.id == PropertyTransaction.buyer_id)
        .outerjoin(Seller, Seller.id == PropertyCommission.seller_id)
    )
    commission_query = apply_filters(
        commission_query, PropertyTransaction.completion_date
    )
    commission_rows = (
        commission_query.with_entities(
            Agent.first_name,
            Agent.last_name,
            func.count(func.distinct(PropertyTransaction.id)).label(
                "transactions_closed"
            ),
            func.coalesce(func.sum(PropertyCommission.commission_amount), 0).label(
                "earned"
            ),
            func.coalesce(func.sum(PropertyCommission.amount_paid), 0).label("paid"),
            func.coalesce(func.sum(PropertyCommission.balance), 0).label("outstanding"),
        )
        .group_by(Agent.id, Agent.first_name, Agent.last_name)
        .order_by(func.sum(PropertyCommission.commission_amount).desc())
        .all()
    )
    total_commission_paid = _money(
        commission_query.with_entities(
            func.coalesce(func.sum(PropertyCommission.amount_paid), 0)
        ).scalar()
    )
    commission_outstanding = _money(
        commission_query.with_entities(
            func.coalesce(func.sum(PropertyCommission.balance), 0)
        ).scalar()
    )

    grouping = request.args.get("grouping", "monthly").strip()
    if grouping not in ("monthly", "quarterly", "yearly"):
        grouping = "monthly"
    period_expression = case(
        (
            grouping == "yearly",
            func.strftime("%Y", PropertyTransaction.completion_date),
        ),
        (
            grouping == "quarterly",
            func.printf(
                "%s Q%d",
                func.strftime("%Y", PropertyTransaction.completion_date),
                (
                    (
                        func.cast(
                            func.strftime("%m", PropertyTransaction.completion_date),
                            db.Integer,
                        )
                        - 1
                    )
                    / 3
                )
                + 1,
            ),
        ),
        else_=func.strftime("%Y-%m", PropertyTransaction.completion_date),
    ).label("period")
    revenue_summary = dict(
        completed_transactions.with_entities(
            period_expression,
            func.coalesce(func.sum(PropertyTransaction.final_sale_price), 0),
        )
        .group_by(period_expression)
        .order_by(period_expression)
        .all()
    )
    payment_summary = dict(
        payment_query.filter(PropertyPayment.payment_type != "Refund")
        .with_entities(
            func.strftime("%Y-%m", PropertyPayment.payment_date),
            func.coalesce(func.sum(PropertyPayment.amount), 0),
        )
        .group_by(func.strftime("%Y-%m", PropertyPayment.payment_date))
        .all()
    )
    periods = list(revenue_summary)
    chart_data = {
        "revenue": {
            "labels": periods,
            "values": [float(revenue_summary[period]) for period in periods],
        },
        "payments": {
            "labels": periods,
            "values": [float(payment_summary.get(period, 0)) for period in periods],
        },
        "outstanding": {
            "labels": periods,
            "values": [float(outstanding_balance) for period in periods],
        },
        "payment_methods": {
            "labels": ["Cash", "Bank Transfer", "Mobile Money", "Cheque", "Other"],
            "values": [],
        },
        "agents": {
            "labels": [
                f"{row.first_name} {row.last_name}" for row in commission_rows[:10]
            ],
            "values": [float(row.earned) for row in commission_rows[:10]],
        },
    }
    method_rows = (
        payment_query.filter(PropertyPayment.payment_type != "Refund")
        .with_entities(
            case(
                (
                    PropertyPayment.payment_method.in_(
                        ("Cash", "Bank Transfer", "Mobile Money", "Cheque")
                    ),
                    PropertyPayment.payment_method,
                ),
                else_="Other",
            ).label("method"),
            func.coalesce(func.sum(PropertyPayment.amount), 0),
        )
        .group_by("method")
        .all()
    )
    method_values = dict(method_rows)
    chart_data["payment_methods"]["values"] = [
        float(method_values.get(label, 0))
        for label in chart_data["payment_methods"]["labels"]
    ]
    summary_rows = [
        {
            "period": period,
            "revenue": revenue_summary[period],
            "payments": payment_summary.get(period, 0),
            "outstanding": outstanding_balance,
            "commissions": total_commission_paid,
        }
        for period in periods
    ]
    filter_params = {key: value for key, value in request.args.items() if key != "page"}
    return render_template(
        "reports/financial.html",
        selected_period=selected_period,
        date_from=start_date.isoformat() if start_date else "",
        date_to=end_date.isoformat() if end_date else "",
        filters=request.args,
        filter_params=filter_params,
        property_types=PROPERTY_TYPE_LABELS,
        statuses=TRANSACTION_STATUSES,
        payment_statuses=("Received", "Refund"),
        payment_methods=("Cash", "Bank Transfer", "Mobile Money", "Cheque", "Other"),
        sellers=Seller.query.order_by(Seller.full_name, Seller.company_name).all(),
        agents=Agent.query.order_by(Agent.first_name, Agent.last_name).all(),
        transactions=transaction_query.options(
            joinedload(PropertyTransaction.property),
            joinedload(PropertyTransaction.buyer),
            joinedload(PropertyTransaction.seller),
            joinedload(PropertyTransaction.sale_agreement).joinedload(
                SaleAgreement.payments
            ),
        )
        .order_by(PropertyTransaction.completion_date.desc())
        .paginate(page=page, per_page=per_page, error_out=False),
        payments=payments,
        outstanding=outstanding,
        commission_rows=commission_rows,
        summary_rows=summary_rows,
        today=date.today(),
        summary={
            "total_revenue": total_revenue,
            "revenue_this_month": revenue_this_month,
            "revenue_this_year": revenue_this_year,
            "total_payments_received": total_payments_received,
            "payments_this_month": payments_this_month,
            "payments_this_year": payments_this_year,
            "pending_payments": pending_payments,
            "outstanding_balance": outstanding_balance,
            "total_commission_paid": total_commission_paid,
            "commission_outstanding": commission_outstanding,
            "average_sale_value": average_sale_value,
            "highest_sale": highest_sale,
            "lowest_sale": lowest_sale,
        },
        chart_data=chart_data,
        grouping=grouping,
    )


@reports.route("/administration")
@reports.route("/administration/", strict_slashes=False)
@require_permission("reports.administration")
def administration_dashboard():
    selected_period, start_date, end_date = _date_window()
    page, per_page = _pagination_args()
    user_id = request.args.get("user_id", "").strip()
    role_name = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    module = request.args.get("module", "").strip()
    notification_type = request.args.get("notification_type", "").strip()
    search = request.args.get("q", "").strip()
    start_at, end_at = _datetime_bounds(start_date, end_date)

    def apply_user_filters(query, date_column=None):
        if date_column is not None:
            query = _apply_datetime_window(query, date_column, start_at, end_at)
        if user_id.isdigit():
            query = query.filter(User.id == int(user_id))
        if role_name:
            query = query.filter(Role.name == role_name)
        if status in ("Active", "Inactive", "Success", "Failed", "Read", "Unread"):
            if status == "Active":
                query = query.filter(User.is_active.is_(True))
            elif status == "Inactive":
                query = query.filter(User.is_active.is_(False))
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                    Role.name.ilike(pattern),
                )
            )
        return query

    last_activity = (
        db.session.query(func.max(ActivityLog.created_at))
        .filter(ActivityLog.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    users_query = apply_user_filters(User.query.outerjoin(Role), User.created_at)
    users = (
        users_query.options(joinedload(User.role_record))
        .order_by(User.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    user_activity_rows = users_query.with_entities(
        User, Role.name.label("role_name"), last_activity.label("last_activity")
    ).all()

    audit_query = AuditLog.query.outerjoin(User).outerjoin(
        Role, Role.id == User.role_id
    )
    audit_query = _apply_datetime_window(
        audit_query, AuditLog.created_at, start_at, end_at
    )
    if user_id.isdigit():
        audit_query = audit_query.filter(AuditLog.user_id == int(user_id))
    if role_name:
        audit_query = audit_query.filter(Role.name == role_name)
    if module:
        audit_query = audit_query.filter(AuditLog.module == module)
    if status in ("Success", "Failed"):
        audit_query = audit_query.filter(AuditLog.status == status)
    if search:
        pattern = f"%{search}%"
        audit_query = audit_query.filter(
            or_(
                AuditLog.event_number.ilike(pattern),
                AuditLog.action.ilike(pattern),
                AuditLog.description.ilike(pattern),
                AuditLog.module.ilike(pattern),
                AuditLog.username.ilike(pattern),
            )
        )
    audit_logs = (
        audit_query.options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    notification_query = Notification.query.join(User).outerjoin(Role)
    notification_query = _apply_datetime_window(
        notification_query, Notification.created_at, start_at, end_at
    )
    if user_id.isdigit():
        notification_query = notification_query.filter(
            Notification.recipient_id == int(user_id)
        )
    if role_name:
        notification_query = notification_query.filter(Role.name == role_name)
    if notification_type:
        notification_query = notification_query.filter(
            Notification.notification_type == notification_type
        )
    if status == "Read":
        notification_query = notification_query.filter(Notification.is_read.is_(True))
    elif status == "Unread":
        notification_query = notification_query.filter(Notification.is_read.is_(False))
    if search:
        pattern = f"%{search}%"
        notification_query = notification_query.filter(
            or_(
                Notification.notification_number.ilike(pattern),
                Notification.title.ilike(pattern),
                Notification.message.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )
    notifications = (
        notification_query.options(joinedload(Notification.recipient))
        .order_by(Notification.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    template_query = _apply_datetime_window(
        EmailTemplate.query, EmailTemplate.created_at, start_at, end_at
    )
    if search:
        pattern = f"%{search}%"
        template_query = template_query.filter(
            or_(
                EmailTemplate.template_name.ilike(pattern),
                EmailTemplate.template_key.ilike(pattern),
            )
        )
    templates = template_query.order_by(EmailTemplate.template_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    backup_query = SystemBackup.query.outerjoin(
        User, User.id == SystemBackup.created_by
    )
    backup_query = _apply_datetime_window(
        backup_query, SystemBackup.created_at, start_at, end_at
    )
    if user_id.isdigit():
        backup_query = backup_query.filter(SystemBackup.created_by == int(user_id))
    if status in ("Pending", "Running", "Completed", "Failed"):
        backup_query = backup_query.filter(SystemBackup.status == status)
    if search:
        pattern = f"%{search}%"
        backup_query = backup_query.filter(
            or_(
                SystemBackup.backup_number.ilike(pattern),
                SystemBackup.backup_name.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )
    backups = (
        backup_query.options(joinedload(SystemBackup.creator))
        .order_by(SystemBackup.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    roles = (
        Role.query.options(joinedload(Role.permissions), joinedload(Role.users))
        .order_by(Role.name)
        .all()
    )
    audit_modules = [
        row[0]
        for row in db.session.query(AuditLog.module)
        .distinct()
        .order_by(AuditLog.module)
        .all()
    ]
    user_activity = dict(
        users_query.with_entities(
            func.strftime("%Y-%m-%d", User.created_at), func.count(User.id)
        )
        .group_by(func.strftime("%Y-%m-%d", User.created_at))
        .order_by(func.strftime("%Y-%m-%d", User.created_at))
        .all()
    )
    audit_activity = dict(
        audit_query.with_entities(
            func.strftime("%Y-%m-%d", AuditLog.created_at), func.count(AuditLog.id)
        )
        .group_by(func.strftime("%Y-%m-%d", AuditLog.created_at))
        .order_by(func.strftime("%Y-%m-%d", AuditLog.created_at))
        .all()
    )
    notification_status = dict(
        notification_query.with_entities(
            case((Notification.is_read.is_(True), "Read"), else_="Unread"),
            func.count(Notification.id),
        )
        .group_by(Notification.is_read)
        .all()
    )
    backup_frequency = dict(
        backup_query.with_entities(
            func.strftime("%Y-%m-%d", SystemBackup.created_at),
            func.count(SystemBackup.id),
        )
        .group_by(func.strftime("%Y-%m-%d", SystemBackup.created_at))
        .order_by(func.strftime("%Y-%m-%d", SystemBackup.created_at))
        .all()
    )
    latest_backup = (
        SystemBackup.query.filter_by(status="Completed")
        .order_by(SystemBackup.created_at.desc())
        .first()
    )
    kpis = {
        "total_users": users_query.count(),
        "active_users": users_query.filter(User.is_active.is_(True)).count(),
        "disabled_users": users_query.filter(User.is_active.is_(False)).count(),
        "administrators": users_query.filter(
            func.lower(Role.name).in_(("administrator", "super administrator"))
        ).count(),
        "total_roles": Role.query.count(),
        "total_permissions": Permission.query.count(),
        "total_notifications": notification_query.count(),
        "total_audit_logs": audit_query.count(),
        "total_templates": template_query.count(),
        "total_backups": backup_query.count(),
        "last_backup_date": latest_backup.created_at if latest_backup else None,
    }
    chart_labels = sorted(
        set(user_activity) | set(audit_activity) | set(backup_frequency)
    )
    chart_data = {
        "user_growth": {
            "labels": chart_labels,
            "values": [user_activity.get(label, 0) for label in chart_labels],
        },
        "roles": {
            "labels": [role.name for role in roles],
            "values": [len(role.users) for role in roles],
        },
        "daily_logins": {
            "labels": chart_labels,
            "values": [user_activity.get(label, 0) for label in chart_labels],
        },
        "audit_activity": {
            "labels": chart_labels,
            "values": [audit_activity.get(label, 0) for label in chart_labels],
        },
        "notifications": {
            "labels": ["Read", "Unread"],
            "values": [
                notification_status.get("Read", 0),
                notification_status.get("Unread", 0),
            ],
        },
        "backups": {
            "labels": chart_labels,
            "values": [backup_frequency.get(label, 0) for label in chart_labels],
        },
    }
    filter_params = {key: value for key, value in request.args.items() if key != "page"}
    return render_template(
        "reports/administration.html",
        selected_period=selected_period,
        date_from=start_date.isoformat() if start_date else "",
        date_to=end_date.isoformat() if end_date else "",
        filters=request.args,
        filter_params=filter_params,
        users_list=User.query.order_by(User.first_name, User.last_name).all(),
        roles=roles,
        audit_modules=audit_modules,
        notification_types=("Information", "Success", "Warning", "Error", "Reminder"),
        users=users,
        user_activity_rows=user_activity_rows,
        audit_logs=audit_logs,
        notifications=notifications,
        templates=templates,
        backups=backups,
        kpis=kpis,
        chart_data=chart_data,
        latest_backup=latest_backup,
    )


REPORT_PERMISSIONS = {
    "executive": "reports.executive",
    "marketplace": "reports.marketplace",
    "transactions": "reports.transactions",
    "financial": "reports.financial",
    "administration": "reports.administration",
}


def _report_export_rows(report_name, start_date, end_date):
    if report_name in {"executive", "transactions", "financial"}:
        query = _apply_date_window(
            PropertyTransaction.query.options(
                joinedload(PropertyTransaction.property),
                joinedload(PropertyTransaction.buyer),
                joinedload(PropertyTransaction.seller),
            ),
            PropertyTransaction.completion_date,
            start_date,
            end_date,
        )
        return [
            {
                "Transaction Number": row.transaction_number,
                "Property": row.property.title if row.property else "N/A",
                "Buyer": _buyer_name_value(row.buyer),
                "Seller": _seller_name_value(row.seller),
                "Sale Amount": row.final_sale_price,
                "Status": row.transaction_status,
                "Date": row.completion_date,
            }
            for row in query.order_by(PropertyTransaction.completion_date.desc()).all()
        ], [
            "Transaction Number",
            "Property",
            "Buyer",
            "Seller",
            "Sale Amount",
            "Status",
            "Date",
        ]
    if report_name == "marketplace":
        query = _apply_datetime_window(
            Property.query.options(
                joinedload(Property.seller), joinedload(Property.agent)
            ),
            Property.created_at,
            *_datetime_bounds(start_date, end_date),
        )
        return [
            {
                "Property Reference": row.listing_number,
                "Title": row.title,
                "Type": row.property_type,
                "Seller": _seller_name_value(row.seller),
                "Agent": row.agent.full_name if row.agent else "N/A",
                "Status": row.status,
                "Created": row.created_at,
            }
            for row in query.order_by(Property.created_at.desc()).all()
        ], [
            "Property Reference",
            "Title",
            "Type",
            "Seller",
            "Agent",
            "Status",
            "Created",
        ]
    query = _apply_datetime_window(
        AuditLog.query, AuditLog.created_at, *_datetime_bounds(start_date, end_date)
    )
    return [
        {
            "Event Number": row.event_number,
            "Date": row.created_at,
            "User": row.username,
            "Action": row.action,
            "Module": row.module,
            "Status": row.status,
            "Description": row.description,
        }
        for row in query.order_by(AuditLog.created_at.desc()).all()
    ], ["Event Number", "Date", "User", "Action", "Module", "Status", "Description"]


def _buyer_name_value(buyer):
    return (
        (buyer.full_name or buyer.company_name or buyer.buyer_number)
        if buyer
        else "N/A"
    )


def _seller_name_value(seller):
    return (
        (seller.full_name or seller.company_name or seller.seller_number)
        if seller
        else "N/A"
    )


@reports.route("/export/<report_name>/<file_format>")
@require_permission("reports.export")
def export_report(report_name, file_format):
    if report_name not in REPORT_PERMISSIONS or file_format not in ("csv", "xlsx"):
        abort(404)
    if not current_user.has_permission(REPORT_PERMISSIONS[report_name]):
        abort(403)
    _, start_date, end_date = _date_window()
    rows, columns = _report_export_rows(report_name, start_date, end_date)
    applied = (
        ", ".join(
            f"{key}={value}" for key, value in request.args.items() if key != "page"
        )
        or "None"
    )
    filters = {
        "date_range": f"{start_date or 'All'} to {end_date or 'All'}",
        "applied": applied,
    }
    record_audit(
        "Export",
        "Reports",
        f"Exported {report_name} report as {file_format} ({len(rows)} rows)",
    )
    return build_report_response(
        report_name.title() + " Reports",
        current_user.email,
        filters,
        columns,
        rows,
        file_format,
        f"{report_name}-report-{datetime.utcnow():%Y%m%d-%H%M%S}",
    )


@reports.route("/saved-filters/<action>", methods=["POST"])
@require_permission("reports.export")
def saved_filters(action):
    saved = session.setdefault("saved_report_filters", {})
    name = request.form.get("name", "").strip()
    if action == "save" and name:
        saved[name] = {
            key: value for key, value in request.form.items() if key != "name"
        }
        session.modified = True
    elif action == "delete" and name:
        saved.pop(name, None)
        session.modified = True
    return redirect(request.form.get("next") or url_for("reports.analytics_dashboard"))


@reports.route("/favorites/<action>/<report_name>", methods=["POST"])
@require_permission("reports.export")
def report_favorite(action, report_name):
    favorites = set(session.get("favorite_reports", []))
    if action == "add":
        favorites.add(report_name)
    elif action == "remove":
        favorites.discard(report_name)
    session["favorite_reports"] = sorted(favorites)
    return redirect(request.form.get("next") or url_for("reports.analytics_dashboard"))


@reports.route("/analytics")
@require_permission("reports.export")
def analytics_dashboard():
    viewed = (
        ActivityLog.query.filter_by(module="Reports", activity_type="View")
        .order_by(ActivityLog.created_at.desc())
        .limit(10)
        .all()
    )
    exports = (
        AuditLog.query.filter_by(module="Reports", action="Export")
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )
    views = dict(
        db.session.query(ActivityLog.title, func.count(ActivityLog.id))
        .filter_by(module="Reports", activity_type="View")
        .group_by(ActivityLog.title)
        .order_by(func.count(ActivityLog.id).desc())
        .limit(10)
        .all()
    )
    export_counts = dict(
        db.session.query(AuditLog.action, func.count(AuditLog.id))
        .filter_by(module="Reports", action="Export")
        .group_by(AuditLog.action)
        .all()
    )
    return render_template(
        "reports/analytics.html",
        viewed=viewed,
        exports=exports,
        favorites=session.get("favorite_reports", []),
        saved_filters=session.get("saved_report_filters", {}),
        chart_data={
            "views": {"labels": list(views), "values": list(views.values())},
            "exports": {
                "labels": list(export_counts),
                "values": list(export_counts.values()),
            },
        },
    )
