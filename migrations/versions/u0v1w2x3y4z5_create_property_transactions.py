"""create property transactions

Revision ID: u0v1w2x3y4z5
Revises: t9u0v1w2x3y4
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa

revision = "u0v1w2x3y4z5"
down_revision = "t9u0v1w2x3y4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_number", sa.String(length=30), nullable=False),
        sa.Column("sale_agreement_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=True),
        sa.Column(
            "final_sale_price", sa.Numeric(precision=18, scale=2), nullable=False
        ),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("transaction_status", sa.String(length=30), nullable=False),
        sa.Column("completed_by", sa.String(length=150), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "final_sale_price > 0", name="ck_transaction_sale_price_positive"
        ),
        sa.ForeignKeyConstraint(
            ["sale_agreement_id"], ["sale_agreements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_number"),
    )
    for name in (
        "transaction_number",
        "sale_agreement_id",
        "property_id",
        "buyer_id",
        "seller_id",
        "transaction_status",
    ):
        op.create_index(
            f"ix_property_transactions_{name}", "property_transactions", [name]
        )
    op.create_index(
        "uq_completed_transaction_property",
        "property_transactions",
        ["property_id"],
        unique=True,
        sqlite_where=sa.text("transaction_status = 'Completed'"),
        postgresql_where=sa.text("transaction_status = 'Completed'"),
    )


def downgrade():
    op.drop_index(
        "uq_completed_transaction_property", table_name="property_transactions"
    )
    for name in (
        "transaction_number",
        "sale_agreement_id",
        "property_id",
        "buyer_id",
        "seller_id",
        "transaction_status",
    ):
        op.drop_index(
            f"ix_property_transactions_{name}", table_name="property_transactions"
        )
    op.drop_table("property_transactions")
