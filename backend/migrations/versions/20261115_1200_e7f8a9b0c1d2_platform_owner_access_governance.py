"""platform_owner_access_governance

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-11-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1. Platform Settings Singleton Table
    if not insp.has_table('platform_settings'):
        op.create_table(
            'platform_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('primary_owner_id', sa.Integer(), nullable=True),
            sa.Column('platform_name', sa.String(length=100), server_default='ServicePulse', nullable=False),
            sa.Column('allow_public_registration', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('bootstrap_completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['primary_owner_id'], ['users.id'], ondelete='RESTRICT'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('platform_settings', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_platform_settings_primary_owner_id'), ['primary_owner_id'], unique=False)

    # 2. Access Requests Table
    if not insp.has_table('access_requests'):
        op.create_table(
            'access_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('request_type', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
            sa.Column('applicant_email', sa.String(length=255), nullable=False),
            sa.Column('applicant_full_name', sa.String(length=150), nullable=False),
            sa.Column('organization_id', sa.Integer(), nullable=True),
            sa.Column('requester_user_id', sa.Integer(), nullable=True),
            sa.Column('target_role_name', sa.String(length=50), nullable=True),
            sa.Column('organization_request_id', sa.Integer(), nullable=True),
            sa.Column('justification', sa.String(length=500), nullable=True),
            sa.Column('rejection_reason', sa.String(length=500), nullable=True),
            sa.Column('client_ip', sa.String(length=50), nullable=True),
            sa.Column('user_agent', sa.String(length=255), nullable=True),
            sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_request_id'], ['organization_requests.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['requester_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('access_requests', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_access_requests_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_access_requests_request_type'), ['request_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_access_requests_status'), ['status'], unique=False)
            batch_op.create_index(batch_op.f('ix_access_requests_applicant_email'), ['applicant_email'], unique=False)
            batch_op.create_index(batch_op.f('ix_access_requests_organization_id'), ['organization_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_access_requests_requester_user_id'), ['requester_user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_access_requests_organization_request_id'), ['organization_request_id'], unique=False)


def downgrade() -> None:
    op.drop_table('access_requests')
    op.drop_table('platform_settings')
