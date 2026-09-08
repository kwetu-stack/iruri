"""add media thumbnail metadata

Revision ID: c7e8f9a0b1c2
Revises: c6d7e8f9a0b1
"""

from alembic import op
import sqlalchemy as sa

revision = "c7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("media_assets", sa.Column("thumbnail_path", sa.String(500)))


def downgrade():
    op.drop_column("media_assets", "thumbnail_path")
