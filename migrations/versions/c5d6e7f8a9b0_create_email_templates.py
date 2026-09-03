"""create email templates

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8, b8c9d0e1f2a3
"""

from alembic import op
import sqlalchemy as sa

revision = "c5d6e7f8a9b0"
down_revision = ("b3c4d5e6f7a8", "b8c9d0e1f2a3")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=150), nullable=False),
        sa.Column("template_name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system_template", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "category IN ('Authentication', 'Marketplace', 'Buyer Engagement', 'Transactions', 'Administration', 'Notifications', 'Marketing')",
            name="ck_email_templates_category",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_key"),
    )
    op.create_index(
        "ix_email_templates_template_key",
        "email_templates",
        ["template_key"],
        unique=False,
    )
    op.create_index(
        "ix_email_templates_category", "email_templates", ["category"], unique=False
    )
    op.create_index(
        "ix_email_templates_is_active", "email_templates", ["is_active"], unique=False
    )


def downgrade():
    op.drop_index("ix_email_templates_is_active", table_name="email_templates")
    op.drop_index("ix_email_templates_category", table_name="email_templates")
    op.drop_index("ix_email_templates_template_key", table_name="email_templates")
    op.drop_table("email_templates")
