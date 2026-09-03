"""Create agencies table

Revision ID: a7b8c9d0e1f2
Revises: f6a1b2c3d4e5
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agency_number", sa.String(length=30), nullable=False),
        sa.Column("agency_name", sa.String(length=200), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("license_number", sa.String(length=100), nullable=True),
        sa.Column("kra_pin", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("alternative_phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("county", sa.String(length=100), nullable=True),
        sa.Column("town", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("postal_address", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year_established", sa.Integer(), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agency_number"),
    )


def downgrade():
    op.drop_table("agencies")
