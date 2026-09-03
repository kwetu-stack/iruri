"""create property reservations

Revision ID: q6r7s8t9u0v1
Revises: p5q6r7s8t9u0
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "q6r7s8t9u0v1"
down_revision = "p5q6r7s8t9u0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reservation_number", sa.String(length=30), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("property_offer_id", sa.Integer(), nullable=False),
        sa.Column("reserved_by", sa.String(length=100), nullable=False),
        sa.Column("reservation_date", sa.DateTime(), nullable=False),
        sa.Column("expiry_date", sa.DateTime(), nullable=False),
        sa.Column("reservation_fee", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "reservation_fee >= 0", name="ck_reservation_fee_non_negative"
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["property_offer_id"], ["property_offers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_offer_id"),
    )
    op.create_index(
        "ix_property_reservations_reservation_number",
        "property_reservations",
        ["reservation_number"],
        unique=True,
    )
    op.create_index(
        "ix_property_reservations_property_id",
        "property_reservations",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        "ix_property_reservations_buyer_id",
        "property_reservations",
        ["buyer_id"],
        unique=False,
    )
    op.create_index(
        "ix_property_reservations_property_offer_id",
        "property_reservations",
        ["property_offer_id"],
        unique=True,
    )
    op.create_index(
        "ix_property_reservations_status",
        "property_reservations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_active_reservation_property",
        "property_reservations",
        ["property_id"],
        unique=True,
        sqlite_where=sa.text("status = 'Active'"),
        postgresql_where=sa.text("status = 'Active'"),
    )


def downgrade():
    op.drop_index("uq_active_reservation_property", table_name="property_reservations")
    op.drop_index("ix_property_reservations_status", table_name="property_reservations")
    op.drop_index(
        "ix_property_reservations_property_offer_id", table_name="property_reservations"
    )
    op.drop_index(
        "ix_property_reservations_buyer_id", table_name="property_reservations"
    )
    op.drop_index(
        "ix_property_reservations_property_id", table_name="property_reservations"
    )
    op.drop_index(
        "ix_property_reservations_reservation_number",
        table_name="property_reservations",
    )
    op.drop_table("property_reservations")
