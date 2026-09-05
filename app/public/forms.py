from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SearchForm:
    location: str = ""
    county: str = ""
    town: str = ""
    property_type: str = ""
    min_price: str = ""
    max_price: str = ""
    bedrooms: str = ""
    bathrooms: str = ""
    keyword: str = ""
    listing_type: str = ""
    sort: str = "newest"

    @classmethod
    def from_args(cls, args):
        return cls(
            location=args.get("location", "").strip(),
            county=args.get("county", "").strip(),
            town=args.get("town", "").strip(),
            property_type=args.get("property_type", "").strip(),
            min_price=args.get("min_price", "").strip(),
            max_price=args.get("max_price", "").strip(),
            bedrooms=args.get("bedrooms", "").strip(),
            bathrooms=args.get("bathrooms", "").strip(),
            keyword=args.get("keyword", "").strip(),
            listing_type=args.get("listing_type", "").strip(),
            sort=args.get("sort", "newest").strip() or "newest",
        )


@dataclass
class EnquiryForm:
    name: str = ""
    email: str = ""
    phone: str = ""
    preferred_contact: str = "Email"
    message: str = ""
    budget: str = ""
    source: str = "Send Enquiry"

    @classmethod
    def from_form(cls, form):
        return cls(
            name=form.get("name", "").strip(),
            email=form.get("email", "").strip(),
            phone=form.get("phone", "").strip(),
            preferred_contact=form.get("preferred_contact", "Email").strip(),
            message=form.get("message", "").strip(),
            budget=form.get("budget", "").strip(),
            source=form.get("source", "Send Enquiry").strip(),
        )

    def validate(self):
        from app.leads.models import LEAD_SOURCES, PREFERRED_CONTACT_METHODS

        errors = []
        if len(self.name) < 2:
            errors.append("Please enter your name.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            errors.append("Please enter a valid email address.")
        if len(self.phone) < 7:
            errors.append("Please enter a valid phone number.")
        if self.preferred_contact not in PREFERRED_CONTACT_METHODS:
            errors.append("Choose a valid preferred contact method.")
        if len(self.message) < 10:
            errors.append("Please include a little more detail in your message.")
        if self.source not in LEAD_SOURCES:
            errors.append("Choose a valid enquiry type.")
        if self.budget:
            try:
                if float(self.budget) < 0:
                    raise ValueError
            except ValueError:
                errors.append("Budget must be a positive number.")
        return errors


@dataclass
class ViewingRequestForm:
    name: str = ""
    email: str = ""
    phone: str = ""
    preferred_date: str = ""
    preferred_time: str = ""
    notes: str = ""

    @classmethod
    def from_form(cls, form):
        return cls(
            name=form.get("visitor_name", "").strip(),
            email=form.get("visitor_email", "").strip(),
            phone=form.get("visitor_phone", "").strip(),
            preferred_date=form.get("preferred_date", "").strip(),
            preferred_time=form.get("preferred_time", "").strip(),
            notes=form.get("additional_notes", "").strip(),
        )

    def validate(self):
        from datetime import date, datetime

        errors = []
        if len(self.name) < 2:
            errors.append("Please enter your name.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            errors.append("Please enter a valid email address.")
        if len(self.phone) < 7:
            errors.append("Please enter a valid phone number.")
        try:
            requested_date = datetime.strptime(self.preferred_date, "%Y-%m-%d").date()
            if requested_date < date.today():
                errors.append("The preferred date cannot be in the past.")
        except ValueError:
            errors.append("Please choose a valid preferred date.")
        try:
            datetime.strptime(self.preferred_time, "%H:%M")
        except ValueError:
            errors.append("Please choose a valid preferred time.")
        return errors
