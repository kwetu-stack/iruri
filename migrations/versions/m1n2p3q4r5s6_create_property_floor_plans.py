"""Create property floor plans table

Revision ID: m1n2p3q4r5s6
Revises: l2g7b8c9d0e1
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "m1n2p3q4r5s6"
down_revision = "l2g7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_floor_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("floor_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_floor_plans_property_id",
        "property_floor_plans",
        ["property_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_property_floor_plans_property_id", table_name="property_floor_plans"
    )
    op.drop_table("property_floor_plans")
