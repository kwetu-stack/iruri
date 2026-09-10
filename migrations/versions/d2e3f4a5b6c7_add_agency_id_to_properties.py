"""Add agency_id to properties

Revision ID: d2e3f4a5b6c7
Revises: c7e8f9a0b1c2
Create Date: 2026-09-10

"""

from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "c7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("properties", schema=None, recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column(
                "agency_id",
                sa.Integer(),
                sa.ForeignKey("agencies.id", name="fk_properties_agency_id_agencies"),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("properties", schema=None, recreate="auto") as batch_op:
        batch_op.drop_column("agency_id")
