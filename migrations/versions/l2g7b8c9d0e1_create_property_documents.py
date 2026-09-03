"""Create property documents table

Revision ID: l2g7b8c9d0e1
Revises: k1f6a7b8c9d0
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "l2g7b8c9d0e1"
down_revision = "k1f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("document_name", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_extension", sa.String(length=10), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_name"),
    )
    op.create_index(
        "ix_property_documents_property_id",
        "property_documents",
        ["property_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_property_documents_property_id", table_name="property_documents")
    op.drop_table("property_documents")
