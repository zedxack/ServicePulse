"""step3_monitoring_and_remediation

Revision ID: a1b2c3d4e5f6
Revises: e6fcf600afa8
Create Date: 2026-11-14 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e6fcf600afa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Device Monitoring Configs
    op.create_table(
        'device_monitoring_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_authorized', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ping_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tcp_ports', sa.String(length=255), nullable=True, server_default='80,443,554,8291'),
        sa.Column('check_interval_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('timeout_seconds', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('consecutive_failure_threshold', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('simulation_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id')
    )
    with op.batch_alter_table('device_monitoring_configs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_device_monitoring_configs_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_device_monitoring_configs_device_id'), ['device_id'], unique=True)

    # 2. Device State Transitions
    op.create_table(
        'device_state_transitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(length=30), nullable=False),
        sa.Column('to_status', sa.String(length=30), nullable=False),
        sa.Column('trigger_reason', sa.String(length=255), nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('transition_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('device_state_transitions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_device_state_transitions_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_device_state_transitions_device_id'), ['device_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_device_state_transitions_transition_at'), ['transition_at'], unique=False)

    # 3. Outage Intervals
    op.create_table(
        'outage_intervals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('is_planned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('outage_intervals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_outage_intervals_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_outage_intervals_device_id'), ['device_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_outage_intervals_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_outage_intervals_incident_id'), ['incident_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_outage_intervals_started_at'), ['started_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_outage_intervals_ended_at'), ['ended_at'], unique=False)

    # 4. Maintenance Windows
    op.create_table(
        'maintenance_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('maintenance_windows', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_maintenance_windows_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_maintenance_windows_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_maintenance_windows_device_id'), ['device_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_maintenance_windows_start_time'), ['start_time'], unique=False)
        batch_op.create_index(batch_op.f('ix_maintenance_windows_end_time'), ['end_time'], unique=False)

    # 5. Extend AgentCommand with simulation flag and remediation link
    with op.batch_alter_table('agent_commands', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_simulation', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('remediation_execution_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_agent_commands_remediation_execution_id'), ['remediation_execution_id'], unique=False)
        batch_op.create_foreign_key('fk_agent_commands_remediation_execution_id', 'remediation_executions', ['remediation_execution_id'], ['id'], ondelete='SET NULL')

    # 6. Extend RemediationExecution with agent command link, simulation flag, and retries
    with op.batch_alter_table('remediation_executions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_command_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_simulation', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index(batch_op.f('ix_remediation_executions_agent_command_id'), ['agent_command_id'], unique=False)
        batch_op.create_foreign_key('fk_remediation_executions_agent_command_id', 'agent_commands', ['agent_command_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('remediation_executions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_remediation_executions_agent_command_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_remediation_executions_agent_command_id'))
        batch_op.drop_column('retry_count')
        batch_op.drop_column('is_simulation')
        batch_op.drop_column('agent_command_id')

    with op.batch_alter_table('agent_commands', schema=None) as batch_op:
        batch_op.drop_constraint('fk_agent_commands_remediation_execution_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_agent_commands_remediation_execution_id'))
        batch_op.drop_column('remediation_execution_id')
        batch_op.drop_column('is_simulation')

    op.drop_table('maintenance_windows')
    op.drop_table('outage_intervals')
    op.drop_table('device_state_transitions')
    op.drop_table('device_monitoring_configs')
