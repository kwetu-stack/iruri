"""create notifications

Revision ID: b8c9d0e1f2a3
Revises: 107cf26be775, c4d5e6f7a8b9
Create Date: 2026-09-03 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = ("107cf26be775", "c4d5e6f7a8b9")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_number", sa.String(length=40), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("related_module", sa.String(length=80), nullable=True),
        sa.Column("related_record_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "notification_type IN ('Information', 'Success', 'Warning', 'Error', 'Reminder')",
            name="ck_notifications_type",
        ),
        sa.CheckConstraint(
            "priority IN ('Low', 'Normal', 'High', 'Critical')",
            name="ck_notifications_priority",
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_number"),
    )
    op.create_index(
        "ix_notifications_notification_number",
        "notifications",
        ["notification_number"],
        unique=True,
    )
    op.create_index(
        "ix_notifications_recipient_id", "notifications", ["recipient_id"], unique=False
    )
    op.create_index(
        "ix_notifications_is_read", "notifications", ["is_read"], unique=False
    )
    op.create_index(
        "ix_notifications_created_at", "notifications", ["created_at"], unique=False
    )


def downgrade():
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_recipient_id", table_name="notifications")
    op.drop_index("ix_notifications_notification_number", table_name="notifications")
    op.drop_table("notifications")
