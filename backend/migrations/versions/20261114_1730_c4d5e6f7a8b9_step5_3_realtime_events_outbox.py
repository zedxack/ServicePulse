"""step5_3_realtime_events_outbox

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-11-14 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('realtime_events'):
        op.create_table(
            'realtime_events',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('organization_id', sa.Integer(), nullable=False),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('payload', sa.Text(), nullable=False),
            sa.Column('target_role', sa.String(length=50), nullable=True),
            sa.Column('origin', sa.String(length=50), server_default='worker', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('realtime_events', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_realtime_events_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_realtime_events_organization_id'), ['organization_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_realtime_events_event_type'), ['event_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_realtime_events_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('realtime_events'):
        with op.batch_alter_table('realtime_events', schema=None) as batch_op:
            for idx in [
                'ix_realtime_events_created_at',
                'ix_realtime_events_event_type',
                'ix_realtime_events_organization_id',
                'ix_realtime_events_id',
            ]:
                try:
                    batch_op.drop_index(batch_op.f(idx))
                except Exception:
                    pass

        op.drop_table('realtime_events')
