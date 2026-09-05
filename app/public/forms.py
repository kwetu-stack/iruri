from dataclasses import dataclass


@dataclass(frozen=True)
class SearchForm:
    location: str = ""
    property_type: str = ""
    min_price: str = ""
    max_price: str = ""
    bedrooms: str = ""

    @classmethod
    def from_args(cls, args):
        return cls(
            location=args.get("location", "").strip(),
            property_type=args.get("property_type", "").strip(),
            min_price=args.get("min_price", "").strip(),
            max_price=args.get("max_price", "").strip(),
            bedrooms=args.get("bedrooms", "").strip(),
        )
