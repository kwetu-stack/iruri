"""Create property videos table

Revision ID: n2o3p4q5r6s7
Revises: m1n2p3q4r5s6
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "n2o3p4q5r6s7"
down_revision = "m1n2p3q4r5s6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_type", sa.String(length=20), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail", sa.String(length=500), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_videos_property_id",
        "property_videos",
        ["property_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_property_videos_property_id", table_name="property_videos")
    op.drop_table("property_videos")
