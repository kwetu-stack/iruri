"""Add location fields to properties

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "o3p4q5r6s7t8"
down_revision = "n2o3p4q5r6s7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("properties", sa.Column("neighbourhood", sa.String(length=150)))
    op.add_column("properties", sa.Column("landmark", sa.String(length=255)))
    op.add_column("properties", sa.Column("postal_code", sa.String(length=20)))
    op.add_column("properties", sa.Column("latitude", sa.Float()))
    op.add_column("properties", sa.Column("longitude", sa.Float()))
    op.add_column("properties", sa.Column("google_map_url", sa.String(length=500)))
    op.create_index("ix_properties_county", "properties", ["county"], unique=False)
    op.create_index("ix_properties_town", "properties", ["town"], unique=False)
    op.create_index("ix_properties_estate", "properties", ["estate"], unique=False)
    op.create_index(
        "ix_properties_neighbourhood", "properties", ["neighbourhood"], unique=False
    )


def downgrade():
    op.drop_index("ix_properties_neighbourhood", table_name="properties")
    op.drop_index("ix_properties_estate", table_name="properties")
    op.drop_index("ix_properties_town", table_name="properties")
    op.drop_index("ix_properties_county", table_name="properties")
    op.drop_column("properties", "google_map_url")
    op.drop_column("properties", "longitude")
    op.drop_column("properties", "latitude")
    op.drop_column("properties", "postal_code")
    op.drop_column("properties", "landmark")
    op.drop_column("properties", "neighbourhood")
