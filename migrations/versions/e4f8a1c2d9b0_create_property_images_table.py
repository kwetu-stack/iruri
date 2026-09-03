"""Create property images table

Revision ID: e4f8a1c2d9b0
Revises: d0c7e7798a43
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "e4f8a1c2d9b0"
down_revision = "d0c7e7798a43"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_cover", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_images_property_id",
        "property_images",
        ["property_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_property_images_property_id", table_name="property_images")
    op.drop_table("property_images")
