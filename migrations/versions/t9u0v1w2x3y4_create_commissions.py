"""create commission management tables

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "t9u0v1w2x3y4"
down_revision = "s8t9u0v1w2x3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_commissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("commission_number", sa.String(length=30), nullable=False),
        sa.Column("sale_agreement_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("agency_id", sa.Integer(), nullable=True),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("commission_type", sa.String(length=40), nullable=False),
        sa.Column("commission_rate", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("sale_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "commission_amount", sa.Numeric(precision=18, scale=2), nullable=False
        ),
        sa.Column("amount_paid", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("payment_status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "commission_rate >= 0 AND commission_rate <= 100",
            name="ck_commission_rate_range",
        ),
        sa.CheckConstraint("sale_price > 0", name="ck_commission_sale_price_positive"),
        sa.CheckConstraint(
            "commission_amount >= 0", name="ck_commission_amount_nonnegative"
        ),
        sa.CheckConstraint(
            "amount_paid >= 0 AND amount_paid <= commission_amount",
            name="ck_commission_paid_range",
        ),
        sa.CheckConstraint("balance >= 0", name="ck_commission_balance_nonnegative"),
        sa.ForeignKeyConstraint(
            ["sale_agreement_id"], ["sale_agreements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("commission_number"),
    )
    for name, columns in (
        ("commission_number", ["commission_number"]),
        ("sale_agreement_id", ["sale_agreement_id"]),
        ("property_id", ["property_id"]),
        ("agent_id", ["agent_id"]),
        ("agency_id", ["agency_id"]),
        ("seller_id", ["seller_id"]),
        ("payment_status", ["payment_status"]),
    ):
        op.create_index(
            f"ix_property_commissions_{name}", "property_commissions", columns
        )
    op.create_table(
        "commission_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("commission_id", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_commission_payment_amount_positive"),
        sa.ForeignKeyConstraint(
            ["commission_id"], ["property_commissions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commission_payments_commission_id", "commission_payments", ["commission_id"]
    )


def downgrade():
    op.drop_index(
        "ix_commission_payments_commission_id", table_name="commission_payments"
    )
    op.drop_table("commission_payments")
    for name in (
        "payment_status",
        "seller_id",
        "agency_id",
        "agent_id",
        "property_id",
        "sale_agreement_id",
        "commission_number",
    ):
        op.drop_index(
            f"ix_property_commissions_{name}", table_name="property_commissions"
        )
    op.drop_table("property_commissions")
