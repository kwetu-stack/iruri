"""create property offers

Revision ID: 4a6b7c8d9e0f
Revises: 398f3945eafd
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "4a6b7c8d9e0f"
down_revision = "398f3945eafd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("offer_number", sa.String(length=30), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("offered_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("buyer_message", sa.Text(), nullable=True),
        sa.Column("seller_response", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_offers_offer_number",
        "property_offers",
        ["offer_number"],
        unique=True,
    )
    op.create_index(
        "ix_property_offers_property_id",
        "property_offers",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        "ix_property_offers_buyer_id", "property_offers", ["buyer_id"], unique=False
    )
    op.create_index(
        "ix_property_offers_agent_id", "property_offers", ["agent_id"], unique=False
    )
    op.create_index(
        "ix_property_offers_status", "property_offers", ["status"], unique=False
    )


def downgrade():
    op.drop_index("ix_property_offers_status", table_name="property_offers")
    op.drop_index("ix_property_offers_agent_id", table_name="property_offers")
    op.drop_index("ix_property_offers_buyer_id", table_name="property_offers")
    op.drop_index("ix_property_offers_property_id", table_name="property_offers")
    op.drop_index("ix_property_offers_offer_number", table_name="property_offers")
    op.drop_table("property_offers")
