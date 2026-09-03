"""Create property features and property feature relationship

Revision ID: k1f6a7b8c9d0
Revises: j0e5f6a7b8c9
Create Date: 2026-09-03

"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "k1f6a7b8c9d0"
down_revision = "j0e5f6a7b8c9"
branch_labels = None
depends_on = None


DEFAULT_FEATURES = {
    "Interior": (
        "Ensuite Bedrooms",
        "Walk-in Closet",
        "Fitted Kitchen",
        "Pantry",
        "Laundry Area",
        "Home Office",
        "Air Conditioning",
    ),
    "Exterior": ("Balcony", "Terrace", "Garden", "Rooftop", "Perimeter Wall"),
    "Construction": (
        "Newly Built",
        "Newly Renovated",
        "Modern Design",
        "Smart Home",
        "Energy Efficient",
    ),
    "Ownership": ("Freehold", "Leasehold"),
    "Location": (
        "Corner Plot",
        "Sea View",
        "Mountain View",
        "Lake View",
        "Gated Community",
    ),
}


def upgrade():
    op.create_table(
        "features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "property_features",
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", "feature_id"),
    )

    features = sa.table(
        "features",
        sa.column("name", sa.String(length=100)),
        sa.column("category", sa.String(length=100)),
        sa.column("created_at", sa.DateTime()),
    )
    created_at = datetime.utcnow()
    op.bulk_insert(
        features,
        [
            {"name": name, "category": category, "created_at": created_at}
            for category, names in DEFAULT_FEATURES.items()
            for name in names
        ],
    )


def downgrade():
    op.drop_table("property_features")
    op.drop_table("features")
