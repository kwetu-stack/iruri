"""create roles and permissions

Revision ID: b3c4d5e6f7a8
Revises: 107cf26be775
Create Date: 2026-09-03 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "107cf26be775"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=False)
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("permission_key", sa.String(length=150), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("permission_key"),
    )
    op.create_index(
        "ix_permissions_permission_key", "permissions", ["permission_key"], unique=False
    )
    op.create_index("ix_permissions_module", "permissions", ["module"], unique=False)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_role_id_roles", "roles", ["role_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_role_id_roles", type="foreignkey")
        batch_op.drop_column("role_id")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_module", table_name="permissions")
    op.drop_index("ix_permissions_permission_key", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
