"""create developments table

Revision ID: b4c5d6e7f8a9
Revises: a62d58b8b336
"""

from alembic import op
import sqlalchemy as sa

revision = "b4c5d6e7f8a9"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "developments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("county", sa.String(length=100), nullable=False),
        sa.Column("town", sa.String(length=100), nullable=False),
        sa.Column("neighbourhood", sa.String(length=150), nullable=True),
        sa.Column("property_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("starting_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("cover_image", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["developer_id"], ["developers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_developments_developer_id", "developments", ["developer_id"])


def downgrade():
    op.drop_index("ix_developments_developer_id", table_name="developments")
    op.drop_table("developments")
