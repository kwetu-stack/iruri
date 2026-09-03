"""Create amenities and property amenities relationship

Revision ID: j0e5f6a7b8c9
Revises: i9d4e5f6a7b8
Create Date: 2026-09-03

"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "j0e5f6a7b8c9"
down_revision = "i9d4e5f6a7b8"
branch_labels = None
depends_on = None


DEFAULT_AMENITIES = (
    "Swimming Pool",
    "Borehole",
    "Gym",
    "Lift",
    "CCTV",
    "Fibre Internet",
    "Solar Power",
    "Garden",
    "Electric Fence",
    "Cabro Parking",
    "Backup Generator",
    "Balcony",
    "Air Conditioning",
    "Water Tank",
    "Servant Quarter",
    "Children's Play Area",
)


def upgrade():
    op.create_table(
        "amenities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "property_amenities",
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("amenity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["amenity_id"], ["amenities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", "amenity_id"),
    )
    amenities = sa.table(
        "amenities",
        sa.column("name", sa.String(length=100)),
        sa.column("created_at", sa.DateTime()),
    )
    created_at = datetime.utcnow()
    op.bulk_insert(
        amenities,
        [{"name": name, "created_at": created_at} for name in DEFAULT_AMENITIES],
    )


def downgrade():
    op.drop_table("property_amenities")
    op.drop_table("amenities")
