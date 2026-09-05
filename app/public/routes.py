from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.agents.models import Agent
from app.agencies.models import Agency
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


def _public_agents_query():
    return Agent.query.filter(
        Agent.is_active.is_(True), Agent.license_number.isnot(None)
    )


def _agent_counties():
    return [
        value
        for (value,) in db.session.query(Agent.county)
        .filter(
            Agent.is_active.is_(True),
            Agent.license_number.isnot(None),
            Agent.county.isnot(None),
        )
        .distinct()
        .order_by(Agent.county)
        .all()
    ]


def _developer_counties():
    return [
        value
        for (value,) in db.session.query(Developer.county)
        .filter(
            Developer.is_active.is_(True),
            Developer.is_verified.is_(True),
            Developer.county.isnot(None),
        )
        .distinct()
        .order_by(Developer.county)
        .all()
    ]


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
    agents = _public_agents_query().order_by(Agent.created_at.desc()).limit(4).all()
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
    county = request.args.get("county", "").strip()
    agency = request.args.get("agency", "").strip()
    name = request.args.get("name", "").strip()
    specialization = request.args.get("specialization", "").strip()
    query = _public_agents_query()
    if county:
        query = query.filter(Agent.county.ilike(f"%{county}%"))
    if name:
        query = query.filter(
            db.or_(
                Agent.first_name.ilike(f"%{name}%"),
                Agent.last_name.ilike(f"%{name}%"),
            )
        )
    if specialization:
        query = query.filter(Agent.bio.ilike(f"%{specialization}%"))
    agents_with_counts = [
        (agent, _available_properties().filter(Property.agent_id == agent.id).count())
        for agent in query.order_by(Agent.created_at.desc()).all()
    ]
    return render_template(
        "public/agents.html",
        agents=agents_with_counts,
        counties=_agent_counties(),
        agencies=[],
        selected_county=county,
        selected_agency=agency,
        selected_name=name,
        selected_specialization=specialization,
    )


@public.get("/agents/<int:id>")
def agent_detail(id):
    if current_user.is_authenticated:
        return redirect(url_for("agents.details", id=id))
    agent = _public_agents_query().filter_by(id=id).first_or_404()
    listings = (
        _available_properties()
        .filter(Property.agent_id == agent.id)
        .options(selectinload(Property.images))
        .order_by(Property.featured.desc(), Property.created_at.desc())
        .all()
    )
    return render_template(
        "public/agent_detail.html",
        agent=agent,
        listings=listings,
        agency=None,
    )


@public.get("/agencies")
def agency_directory():
    county = request.args.get("county", "").strip()
    query = Agency.query.filter_by(is_active=True)
    if county:
        query = query.filter(Agency.county.ilike(f"%{county}%"))
    agencies = query.order_by(Agency.agency_name).all()
    return render_template(
        "public/agencies.html",
        agencies=agencies,
        counties=[
            value
            for (value,) in db.session.query(Agency.county)
            .filter(Agency.is_active.is_(True), Agency.county.isnot(None))
            .distinct()
            .order_by(Agency.county)
            .all()
        ],
        selected_county=county,
    )


@public.get("/agencies/<int:id>")
def agency_detail(id):
    if current_user.is_authenticated:
        return redirect(url_for("agencies.details", id=id))
    agency = Agency.query.filter_by(id=id, is_active=True).first_or_404()
    return render_template(
        "public/agency_detail.html",
        agency=agency,
        team_members=[],
        listings=[],
        featured_properties=[],
    )


@public.get("/developers")
def developers():
    county = request.args.get("county", "").strip()
    project_type = request.args.get("project_type", "").strip()
    query = Developer.query.filter_by(is_active=True, is_verified=True)
    if county:
        query = query.filter(Developer.county.ilike(f"%{county}%"))
    developers_list = query.order_by(Developer.created_at.desc()).all()
    if project_type:
        developers_list = [
            developer
            for developer in developers_list
            if any(
                (property.property_type or "").lower() == project_type.lower()
                for property in developer.properties
                if property.status
                and property.status.lower()
                in {status.lower() for status in PUBLIC_STATUSES}
            )
        ]
    return render_template(
        "public/developers.html",
        developers=developers_list,
        counties=_developer_counties(),
        project_types=["Apartment", "House", "Land", "Commercial"],
        selected_county=county,
        selected_project_type=project_type,
    )


@public.get("/developers/<int:id>")
def developer_detail(id):
    if current_user.is_authenticated:
        return redirect(url_for("developers.details", id=id))
    developer = Developer.query.filter_by(
        id=id, is_active=True, is_verified=True
    ).first_or_404()
    current_developments = (
        _available_properties()
        .filter(Property.developer_id == developer.id)
        .options(selectinload(Property.images))
        .order_by(Property.featured.desc(), Property.created_at.desc())
        .all()
    )
    return render_template(
        "public/developer_detail.html",
        developer=developer,
        current_developments=current_developments,
        completed_developments=[],
        featured_projects=[
            property for property in current_developments if property.featured
        ],
    )


@public.get("/about")
def about():
    return render_template("public/about.html")


@public.get("/contact")
def contact():
    return render_template("public/contact.html")
