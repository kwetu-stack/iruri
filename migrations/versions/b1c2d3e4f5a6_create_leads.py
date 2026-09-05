"""create leads

Revision ID: b1c2d3e4f5a6
Revises: a62d58b8b336
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a62d58b8b336"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference_number", sa.String(length=40), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("preferred_contact", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("budget", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('New', 'Contacted', 'Viewing Scheduled', 'Negotiating', 'Closed', 'Lost')",
            name="ck_leads_status",
        ),
        sa.CheckConstraint(
            "preferred_contact IN ('Email', 'Phone', 'WhatsApp')",
            name="ck_leads_preferred_contact",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_number"),
    )
    for name in (
        "reference_number",
        "property_id",
        "agent_id",
        "email",
        "status",
        "created_at",
    ):
        op.create_index(f"ix_leads_{name}", "leads", [name])


def downgrade():
    for name in (
        "reference_number",
        "property_id",
        "agent_id",
        "email",
        "status",
        "created_at",
    ):
        op.drop_index(f"ix_leads_{name}", table_name="leads")
    op.drop_table("leads")
