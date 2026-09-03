"""create system settings

Revision ID: 4b5c6d7e8f90
Revises: 398f3945eafd
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "4b5c6d7e8f90"
down_revision = "398f3945eafd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("setting_key", sa.String(length=150), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data_type", sa.String(length=20), nullable=False),
        sa.Column("is_editable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "category IN ('General', 'Company', 'Marketplace', 'Transactions', "
            "'Notifications', 'Security', 'Email', 'Appearance')",
            name="ck_system_settings_category",
        ),
        sa.CheckConstraint(
            "data_type IN ('string', 'integer', 'float', 'boolean', 'json')",
            name="ck_system_settings_data_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )
    op.create_index(
        "ix_system_settings_setting_key",
        "system_settings",
        ["setting_key"],
        unique=True,
    )
    op.create_index(
        "ix_system_settings_category", "system_settings", ["category"], unique=False
    )


def downgrade():
    op.drop_index("ix_system_settings_category", table_name="system_settings")
    op.drop_index("ix_system_settings_setting_key", table_name="system_settings")
    op.drop_table("system_settings")
