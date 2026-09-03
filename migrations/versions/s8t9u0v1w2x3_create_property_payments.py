"""create property payments

Revision ID: s8t9u0v1w2x3
Revises: r7s8t9u0v1w2
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "s8t9u0v1w2x3"
down_revision = "r7s8t9u0v1w2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_number", sa.String(length=30), nullable=False),
        sa.Column("sale_agreement_id", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_type", sa.String(length=30), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("received_by", sa.String(length=150), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("receipt_number", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_property_payment_amount_positive"),
        sa.ForeignKeyConstraint(
            ["sale_agreement_id"], ["sale_agreements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_number"),
        sa.UniqueConstraint("receipt_number"),
    )
    op.create_index(
        "ix_property_payments_payment_number",
        "property_payments",
        ["payment_number"],
        unique=True,
    )
    op.create_index(
        "ix_property_payments_sale_agreement_id",
        "property_payments",
        ["sale_agreement_id"],
    )


def downgrade():
    op.drop_index(
        "ix_property_payments_sale_agreement_id", table_name="property_payments"
    )
    op.drop_index("ix_property_payments_payment_number", table_name="property_payments")
    op.drop_table("property_payments")
