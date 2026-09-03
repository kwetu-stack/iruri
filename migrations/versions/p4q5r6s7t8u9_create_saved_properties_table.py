"""Create saved properties table

Revision ID: p4q5r6s7t8u9
Revises: o3p4q5r6s7t8
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "p4q5r6s7t8u9"
down_revision = "o3p4q5r6s7t8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_properties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "buyer_id", "property_id", name="uq_saved_property_buyer_property"
        ),
    )
    op.create_index(
        "ix_saved_properties_buyer_id", "saved_properties", ["buyer_id"], unique=False
    )
    op.create_index(
        "ix_saved_properties_property_id",
        "saved_properties",
        ["property_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_saved_properties_property_id", table_name="saved_properties")
    op.drop_index("ix_saved_properties_buyer_id", table_name="saved_properties")
    op.drop_table("saved_properties")
