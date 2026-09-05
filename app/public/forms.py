from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SearchForm:
    location: str = ""
    property_type: str = ""
    min_price: str = ""
    max_price: str = ""
    bedrooms: str = ""
    listing_type: str = ""

    @classmethod
    def from_args(cls, args):
        return cls(
            location=args.get("location", "").strip(),
            property_type=args.get("property_type", "").strip(),
            min_price=args.get("min_price", "").strip(),
            max_price=args.get("max_price", "").strip(),
            bedrooms=args.get("bedrooms", "").strip(),
            listing_type=args.get("listing_type", "").strip(),
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
