"""Add marketplace relationships to properties

Revision ID: i9d4e5f6a7b8
Revises: h8c3d4e5f6a7
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "i9d4e5f6a7b8"
down_revision = "h8c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    properties_exist = bind.execute(sa.text("SELECT 1 FROM properties LIMIT 1")).first()
    legacy_seller_id = None
    if properties_exist:
        legacy_seller_id = bind.execute(
            sa.text("SELECT id FROM sellers ORDER BY id LIMIT 1")
        ).scalar()
        if legacy_seller_id is None:
            legacy_seller_id = bind.execute(
                sa.text(
                    "INSERT INTO sellers "
                    "(seller_number, seller_type, phone, full_name, verified, active) "
                    "VALUES (:seller_number, :seller_type, :phone, :full_name, :verified, :active)"
                ),
                {
                    "seller_number": "IRR-MIGRATED-001",
                    "seller_type": "Individual",
                    "phone": "N/A",
                    "full_name": "Legacy Property Owner",
                    "verified": False,
                    "active": True,
                },
            ).lastrowid

    with op.batch_alter_table("properties", schema=None, recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "seller_id",
                sa.Integer(),
                sa.ForeignKey("sellers.id", name="fk_properties_seller_id_sellers"),
                nullable=True,
            )
        )

    if legacy_seller_id is not None:
        bind.execute(
            sa.text("UPDATE properties SET seller_id = :seller_id"),
            {"seller_id": legacy_seller_id},
        )

    with op.batch_alter_table("properties", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "seller_id",
            existing_type=sa.Integer(),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.add_column(
            sa.Column(
                "developer_id",
                sa.Integer(),
                sa.ForeignKey(
                    "developers.id", name="fk_properties_developer_id_developers"
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "agent_id",
                sa.Integer(),
                sa.ForeignKey("agents.id", name="fk_properties_agent_id_agents"),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("properties", schema=None, recreate="always") as batch_op:
        batch_op.drop_column("agent_id")
        batch_op.drop_column("developer_id")
        batch_op.drop_column("seller_id")
