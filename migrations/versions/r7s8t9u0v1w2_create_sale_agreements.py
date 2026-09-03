"""create sale agreements

Revision ID: r7s8t9u0v1w2
Revises: q6r7s8t9u0v1
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "r7s8t9u0v1w2"
down_revision = "q6r7s8t9u0v1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sale_agreements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agreement_number", sa.String(length=30), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("agreed_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("agreement_date", sa.Date(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("agreed_price > 0", name="ck_sale_agreement_price_positive"),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["property_reservations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agreement_number"),
    )
    op.create_index(
        "ix_sale_agreements_agreement_number",
        "sale_agreements",
        ["agreement_number"],
        unique=True,
    )
    op.create_index(
        "ix_sale_agreements_reservation_id", "sale_agreements", ["reservation_id"]
    )
    op.create_index(
        "ix_sale_agreements_property_id", "sale_agreements", ["property_id"]
    )
    op.create_index("ix_sale_agreements_buyer_id", "sale_agreements", ["buyer_id"])
    op.create_index("ix_sale_agreements_seller_id", "sale_agreements", ["seller_id"])
    op.create_index("ix_sale_agreements_status", "sale_agreements", ["status"])
    op.create_index(
        "uq_active_sale_agreement_reservation",
        "sale_agreements",
        ["reservation_id"],
        unique=True,
        sqlite_where=sa.text("status = 'Active'"),
        postgresql_where=sa.text("status = 'Active'"),
    )


def downgrade():
    op.drop_index("uq_active_sale_agreement_reservation", table_name="sale_agreements")
    op.drop_index("ix_sale_agreements_status", table_name="sale_agreements")
    op.drop_index("ix_sale_agreements_seller_id", table_name="sale_agreements")
    op.drop_index("ix_sale_agreements_buyer_id", table_name="sale_agreements")
    op.drop_index("ix_sale_agreements_property_id", table_name="sale_agreements")
    op.drop_index("ix_sale_agreements_reservation_id", table_name="sale_agreements")
    op.drop_index("ix_sale_agreements_agreement_number", table_name="sale_agreements")
    op.drop_table("sale_agreements")
