"""
ServicePulse - Remediation Worker & Agent Command Simulation Engine
Processes pending remediation commands, runs safe simulation adapters for test devices,
and enforces observable verification requirements.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.agent import AgentCommand
from backend.app.services.remediation_verification import RemediationVerification


class RemediationWorker:
    """
    Background processor for remediation commands and simulation adapter.
    """

    @staticmethod
    async def process_pending_commands(db: AsyncSession) -> int:
        """
        Process pending agent commands:
        - If is_simulation is True: simulate execution through the full lifecycle:
          pending -> dispatched -> executing -> succeeded.
        - Verify observable evidence via RemediationVerification.
        Returns count of commands processed.
        """
        now = datetime.now(timezone.utc)
        q = (
            select(AgentCommand)
            .where(AgentCommand.status == "pending")
            .limit(20)
        )
        commands = list((await db.execute(q)).scalars().all())
        processed_count = 0

        for cmd in commands:
            if cmd.is_simulation:
                # Progress through command states
                cmd.status = "dispatched"
                await db.flush()

                cmd.status = "executing"
                await db.flush()

                cmd.status = "succeeded"
                cmd.executed_at = now
                cmd.execution_result = f"SIMULATION: Simulated execution of '{cmd.action_name}' succeeded."
                db.add(cmd)
                await db.flush()

                # Trigger verification
                if cmd.remediation_execution_id:
                    await RemediationVerification.verify_execution(cmd.remediation_execution_id, db)

                processed_count += 1
            else:
                # Live agent commands remain pending until real agent picks them up
                pass

        await db.commit()
        return processed_count
