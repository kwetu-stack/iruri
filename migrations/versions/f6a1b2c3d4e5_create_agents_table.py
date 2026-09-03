"""Create agents table

Revision ID: f6a1b2c3d4e5
Revises: e4f8a1c2d9b0
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "f6a1b2c3d4e5"
down_revision = "e4f8a1c2d9b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_number", sa.String(length=30), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("gender", sa.String(length=30), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("national_id", sa.String(length=100), nullable=True),
        sa.Column("license_number", sa.String(length=100), nullable=True),
        sa.Column("kra_pin", sa.String(length=100), nullable=True),
        sa.Column("county", sa.String(length=100), nullable=True),
        sa.Column("town", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("commission_rate", sa.Float(), nullable=True),
        sa.Column("profile_photo", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_number"),
    )


def downgrade():
    op.drop_table("agents")
