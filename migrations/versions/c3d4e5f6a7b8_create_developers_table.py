"""Create developers table

Revision ID: c3d4e5f6a7b8
Revises: a7b8c9d0e1f2
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "developers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_number", sa.String(length=30), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
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
        sa.Column("specialization", sa.String(length=255), nullable=True),
        sa.Column("total_projects", sa.Integer(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("developer_number"),
    )


def downgrade():
    op.drop_table("developers")
