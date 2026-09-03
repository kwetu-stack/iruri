"""Create sellers table

Revision ID: g7b2c3d4e5f6
Revises: c3d4e5f6a7b8
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "g7b2c3d4e5f6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sellers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_number", sa.String(length=30), nullable=False),
        sa.Column("seller_type", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("national_id", sa.String(length=100), nullable=True),
        sa.Column("passport_number", sa.String(length=100), nullable=True),
        sa.Column("kra_pin", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("alternative_phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("county", sa.String(length=100), nullable=True),
        sa.Column("town", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("postal_address", sa.String(length=255), nullable=True),
        sa.Column("profile_photo", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seller_number"),
    )


def downgrade():
    op.drop_table("sellers")
