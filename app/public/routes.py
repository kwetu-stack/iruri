from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload
from flask import abort, flash, render_template, request, url_for

from app.agents.models import Agent
from app.developers.models import Developer
from app.extensions import db
from app.audit.service import record_audit
from app.leads.models import Lead
from app.notifications.service import administrator_users, notify_profile, notify_users
from app.properties.models import Property
from app.public import public
from app.public.forms import EnquiryForm, SearchForm

PROPERTY_IMAGE = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80"
HERO_IMAGE = "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=2200&q=85"
PUBLIC_STATUSES = ("Published", "Available", "Visible")


def _available_properties(listing_type=None):
    query = Property.query.filter(
        db.func.lower(Property.status).in_(
            [status.lower() for status in PUBLIC_STATUSES]
        )
    )
    if listing_type:
        query = query.filter(
            db.func.lower(Property.listing_type).contains(listing_type.lower())
        )
    return query


def _apply_search(query, form):
    if form.location:
        location = f"%{form.location}%"
        query = query.filter(
            or_(
                Property.county.ilike(location),
                Property.town.ilike(location),
                Property.estate.ilike(location),
                Property.neighbourhood.ilike(location),
            )
        )
    if form.property_type:
        query = query.filter(
            db.func.lower(Property.property_type) == form.property_type.lower()
        )
    if form.min_price:
        try:
            query = query.filter(Property.price >= float(form.min_price))
        except ValueError:
            pass
    if form.max_price:
        try:
            query = query.filter(Property.price <= float(form.max_price))
        except ValueError:
            pass
    if form.bedrooms:
        try:
            query = query.filter(Property.bedrooms >= int(form.bedrooms))
        except ValueError:
            pass
    return query


def _property_page(listing_type=None):
    form = SearchForm.from_args(request.args)
    listing_type = listing_type or form.listing_type.lower() or None
    page = request.args.get("page", 1, type=int)
    query = _apply_search(_available_properties(listing_type), form)
    listings = (
        query.options(
            joinedload(Property.agent),
            joinedload(Property.developer),
            selectinload(Property.images),
        )
        .order_by(Property.created_at.desc())
        .paginate(page=max(page, 1), per_page=12, error_out=False)
    )
    return render_template(
        "public/listings.html",
        listings=listings,
        form=form,
        listing_type=listing_type,
        public_statuses=PUBLIC_STATUSES,
    )


@public.get("/")
def home():
    featured = (
        _available_properties()
        .filter(Property.featured.is_(True))
        .options(selectinload(Property.images))
        .order_by(Property.created_at.desc())
        .limit(6)
        .all()
    )
    latest = (
        _available_properties()
        .options(selectinload(Property.images))
        .order_by(Property.created_at.desc())
        .limit(4)
        .all()
    )
    agents = (
        Agent.query.filter_by(is_active=True)
        .order_by(Agent.created_at.desc())
        .limit(4)
        .all()
    )
    developers = (
        Developer.query.filter_by(is_active=True)
        .order_by(Developer.is_verified.desc(), Developer.created_at.desc())
        .limit(4)
        .all()
    )
    return render_template(
        "public/home.html",
        featured=featured,
        latest=latest,
        agents=agents,
        developers=developers,
        stats={
            "properties": _available_properties().count(),
            "agents": Agent.query.filter_by(is_active=True).count(),
            "developers": Developer.query.filter_by(is_active=True).count(),
            "clients": 1200,
        },
        hero_image=HERO_IMAGE,
        property_image=PROPERTY_IMAGE,
        form=SearchForm.from_args(request.args),
    )


@public.get("/buy")
def buy():
    return _property_page("sale")


@public.get("/rent")
def rent():
    return _property_page("rent")


@public.get("/properties")
def properties():
    return _property_page()


@public.route("/properties/<int:id>", methods=["GET", "POST"])
@public.route("/property/<int:id>", methods=["GET", "POST"])
def property_detail(id):
    property_record = (
        Property.query.options(
            joinedload(Property.agent),
            joinedload(Property.developer),
            selectinload(Property.images),
        )
        .filter(
            Property.id == id,
            db.func.lower(Property.status).in_(
                [status.lower() for status in PUBLIC_STATUSES]
            ),
        )
        .first()
    )
    if property_record is None:
        abort(404)
    form = (
        EnquiryForm.from_form(request.form)
        if request.method == "POST"
        else EnquiryForm()
    )
    if request.method == "POST":
        errors = form.validate()
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            lead = Lead(
                reference_number="TEMP",
                property_id=property_record.id,
                agent_id=property_record.agent_id,
                name=form.name,
                email=form.email,
                phone=form.phone,
                preferred_contact=form.preferred_contact,
                message=form.message,
                budget=float(form.budget) if form.budget else None,
                source=form.source,
                status="New",
            )
            db.session.add(lead)
            db.session.flush()
            lead.reference_number = f"LED-{lead.created_at.year}-{lead.id:06d}"
            notification_values = {
                "title": "New property lead",
                "message": f"{lead.name} sent an enquiry for {property_record.title}.",
                "notification_type": "Information",
                "priority": "High",
                "action_url": url_for("leads.detail", lead_id=lead.id),
                "related_module": "Leads",
                "related_record_id": lead.id,
            }
            notify_users(administrator_users(), **notification_values)
            notify_profile(property_record.agent, **notification_values)
            record_audit(
                "Lead created",
                "Leads",
                f"Lead {lead.reference_number} created for {property_record.title}",
                "Lead",
                lead.id,
                commit=False,
            )
            db.session.commit()
            return render_template(
                "public/property_detail.html",
                property=property_record,
                form=EnquiryForm(),
                submitted=True,
            )
    return render_template(
        "public/property_detail.html", property=property_record, form=form
    )


@public.get("/agents")
def agents():
    agent_list = (
        Agent.query.filter_by(is_active=True).order_by(Agent.created_at.desc()).all()
    )
    return render_template("public/agents.html", agents=agent_list)


@public.get("/developers")
def developers():
    developer_list = (
        Developer.query.filter_by(is_active=True)
        .order_by(Developer.is_verified.desc(), Developer.created_at.desc())
        .all()
    )
    return render_template("public/developers.html", developers=developer_list)


@public.get("/about")
def about():
    return render_template("public/about.html")


@public.get("/contact")
def contact():
    return render_template("public/contact.html")
