"""auth_registration_onboarding

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-11-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table('organization_invitations'):
        op.create_table(
            'organization_invitations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('organization_id', sa.Integer(), nullable=False),
            sa.Column('role_id', sa.Integer(), nullable=False),
            sa.Column('token_hash', sa.String(length=64), nullable=False),
            sa.Column('token_prefix', sa.String(length=16), nullable=False),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.Column('max_uses', sa.Integer(), server_default='1', nullable=False),
            sa.Column('uses_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_revoked', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('revoked_by_id', sa.Integer(), nullable=True),
            sa.Column('invited_email', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['revoked_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('organization_invitations', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_organization_invitations_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_organization_invitations_organization_id'), ['organization_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_organization_invitations_role_id'), ['role_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_organization_invitations_token_hash'), ['token_hash'], unique=True)
            batch_op.create_index(batch_op.f('ix_organization_invitations_expires_at'), ['expires_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_organization_invitations_is_revoked'), ['is_revoked'], unique=False)

    if not insp.has_table('organization_requests'):
        op.create_table(
            'organization_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('org_name', sa.String(length=150), nullable=False),
            sa.Column('org_slug', sa.String(length=50), nullable=False),
            sa.Column('org_email', sa.String(length=255), nullable=False),
            sa.Column('org_domain', sa.String(length=100), nullable=True),
            sa.Column('contact_full_name', sa.String(length=150), nullable=False),
            sa.Column('contact_email', sa.String(length=255), nullable=False),
            sa.Column('hashed_password', sa.String(length=255), nullable=False),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('website', sa.String(length=255), nullable=True),
            sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
            sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('rejection_reason', sa.String(length=500), nullable=True),
            sa.Column('created_organization_id', sa.Integer(), nullable=True),
            sa.Column('created_user_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['created_organization_id'], ['organizations.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('organization_requests', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_organization_requests_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_organization_requests_org_slug'), ['org_slug'], unique=True)
            batch_op.create_index(batch_op.f('ix_organization_requests_contact_email'), ['contact_email'], unique=False)
            batch_op.create_index(batch_op.f('ix_organization_requests_status'), ['status'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table('organization_requests'):
        with op.batch_alter_table('organization_requests', schema=None) as batch_op:
            for idx in [
                'ix_organization_requests_status',
                'ix_organization_requests_contact_email',
                'ix_organization_requests_org_slug',
                'ix_organization_requests_id',
            ]:
                try:
                    batch_op.drop_index(batch_op.f(idx))
                except Exception:
                    pass
        op.drop_table('organization_requests')

    if insp.has_table('organization_invitations'):
        with op.batch_alter_table('organization_invitations', schema=None) as batch_op:
            for idx in [
                'ix_organization_invitations_is_revoked',
                'ix_organization_invitations_expires_at',
                'ix_organization_invitations_token_hash',
                'ix_organization_invitations_role_id',
                'ix_organization_invitations_organization_id',
                'ix_organization_invitations_id',
            ]:
                try:
                    batch_op.drop_index(batch_op.f(idx))
                except Exception:
                    pass
        op.drop_table('organization_invitations')
