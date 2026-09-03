"""create offer negotiation history

Revision ID: p5q6r7s8t9u0
Revises: 4a6b7c8d9e0f, o3p4q5r6s7t8
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "p5q6r7s8t9u0"
down_revision = ("4a6b7c8d9e0f", "o3p4q5r6s7t8")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "offer_negotiations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_offer_id", sa.Integer(), nullable=False),
        sa.Column("offered_by", sa.String(length=50), nullable=False),
        sa.Column("offered_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["property_offer_id"], ["property_offers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_offer_negotiations_property_offer_id",
        "offer_negotiations",
        ["property_offer_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_offer_negotiations_property_offer_id", table_name="offer_negotiations"
    )
    op.drop_table("offer_negotiations")
