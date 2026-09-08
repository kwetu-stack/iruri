"""create centralized media asset metadata

Revision ID: c6d7e8f9a0b1
Revises: b4c5d6e7f8a9
"""

from alembic import op
import sqlalchemy as sa

revision = "c6d7e8f9a0b1"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_extension", sa.String(20), nullable=False),
        sa.Column("mime_type", sa.String(150), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("duration", sa.Numeric(12, 3)),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("public_url", sa.String(500), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("module", sa.String(80), nullable=False),
        sa.Column("record_id", sa.Integer()),
        sa.Column("is_cover", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
    )
    op.create_index("ix_media_assets_checksum", "media_assets", ["checksum"])
    op.create_index("ix_media_assets_module", "media_assets", ["module"])
    op.create_index("ix_media_assets_record_id", "media_assets", ["record_id"])
    op.create_index("ix_media_assets_status", "media_assets", ["status"])


def downgrade():
    op.drop_table("media_assets")
