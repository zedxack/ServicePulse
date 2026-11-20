"""step5_3_notifications

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-11-14 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('notifications'):
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('organization_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('target_role', sa.String(length=50), nullable=True),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(length=20), server_default='info', nullable=False),
            sa.Column('category', sa.String(length=50), server_default='device', nullable=False),
            sa.Column('fingerprint', sa.String(length=128), nullable=False),
            sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('is_dismissed', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('data', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('notifications', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_notifications_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_organization_id'), ['organization_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_target_role'), ['target_role'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_severity'), ['severity'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_category'), ['category'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_fingerprint'), ['fingerprint'], unique=False)
            batch_op.create_index(batch_op.f('ix_notifications_is_read'), ['is_read'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('notifications'):
        with op.batch_alter_table('notifications', schema=None) as batch_op:
            for idx in [
                'ix_notifications_is_read',
                'ix_notifications_fingerprint',
                'ix_notifications_category',
                'ix_notifications_severity',
                'ix_notifications_target_role',
                'ix_notifications_user_id',
                'ix_notifications_organization_id',
                'ix_notifications_id',
            ]:
                try:
                    batch_op.drop_index(batch_op.f(idx))
                except Exception:
                    pass

        op.drop_table('notifications')
