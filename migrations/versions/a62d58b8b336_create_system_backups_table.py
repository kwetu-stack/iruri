"""create system backups table

Revision ID: a62d58b8b336
Revises: d6e7f8a9b0c1
Create Date: 2026-09-04 08:40:06.191753

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a62d58b8b336'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('system_backups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('backup_number', sa.String(length=30), nullable=False),
    sa.Column('backup_name', sa.String(length=200), nullable=False),
    sa.Column('backup_type', sa.String(length=30), nullable=False),
    sa.Column('storage_location', sa.String(length=255), nullable=True),
    sa.Column('file_size', sa.String(length=50), nullable=True),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("backup_type IN ('Manual', 'Scheduled', 'Before Upgrade', 'Before Restore')", name='ck_system_backups_backup_type'),
    sa.CheckConstraint("status IN ('Pending', 'Running', 'Completed', 'Failed')", name='ck_system_backups_status'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('system_backups', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_system_backups_backup_number'), ['backup_number'], unique=True)


def downgrade():
    with op.batch_alter_table('system_backups', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_system_backups_backup_number'))

    op.drop_table('system_backups')
