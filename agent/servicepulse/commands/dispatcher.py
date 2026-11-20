"""
ServicePulse Native Windows Agent - Command Dispatcher & Lifecycle Manager
Orchestrates command polling, validation, execution, and result submission.
Author: Muhammadyusuf Usmonov
"""
import datetime
from typing import Any, Dict, Set

from servicepulse.api_client import ApiClient
from servicepulse.commands.execution import CommandExecutor, ExecutionResult
from servicepulse.commands.schemas import (
    DiagnosticCheckParams,
    InstallApprovedSoftwareParams,
    NotifyAdminParams,
    RecheckNetworkParams,
    RestartAgentParams,
    RestartServiceParams,
    parse_and_validate_command_parameters,
)
from servicepulse.commands.verification import CommandVerifier
from servicepulse.logging.setup import get_logger

logger = get_logger()


class CommandDispatcher:
    """
    Manages the AgentCommand lifecycle:
    pending -> acknowledged -> executing -> succeeded / failed.
    """

    def __init__(self, api_client: ApiClient, simulation_mode: bool = False, max_command_age_seconds: int = 3600):
        self.api_client = api_client
        self.simulation_mode = simulation_mode
        self.max_command_age_seconds = max_command_age_seconds
        self._processed_command_ids: Set[int] = set()

    def poll_and_process_commands(self) -> int:
        """
        Poll pending commands from backend and process each through its lifecycle.
        Returns count of commands processed.
        """
        try:
            pending_commands = self.api_client.get_pending_commands()
        except Exception as e:
            logger.debug(f"Unable to poll commands: {e}")
            return 0

        if not pending_commands:
            return 0

        logger.info(f"Retrieved {len(pending_commands)} pending commands from backend.")
        processed_count = 0

        for cmd in pending_commands:
            cmd_id = cmd.get("id")
            if not cmd_id:
                continue

            self._process_single_command(cmd)
            processed_count += 1

        return processed_count

    def _process_single_command(self, cmd: Dict[str, Any]) -> None:
        """Process an individual command safely."""
        cmd_id = cmd["id"]
        action_name = cmd.get("action_name", "")
        raw_params = cmd.get("parameters")
        is_sim = cmd.get("is_simulation", False) or self.simulation_mode

        # 0. Deduplication check
        if cmd_id in self._processed_command_ids:
            logger.warning(f"Command #{cmd_id} was already executed; skipping duplicate dispatch.")
            return

        logger.info(f"Processing command #{cmd_id} ('{action_name}', simulation={is_sim})")

        # 1. Acknowledge receipt
        try:
            self.api_client.acknowledge_command(cmd_id)
        except Exception as e:
            logger.warning(f"Failed to acknowledge command #{cmd_id}: {e}")

        # Mark as seen in processed cache
        self._processed_command_ids.add(cmd_id)

        # 2. Expiration check
        created_at_raw = cmd.get("created_at")
        if created_at_raw:
            try:
                if isinstance(created_at_raw, str):
                    # Handle ISO string with trailing Z or timezone
                    clean_ts = created_at_raw.replace("Z", "+00:00")
                    created_dt = datetime.datetime.fromisoformat(clean_ts)
                elif isinstance(created_at_raw, datetime.datetime):
                    created_dt = created_at_raw
                else:
                    created_dt = None

                if created_dt:
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=datetime.timezone.utc)
                    age_seconds = (datetime.datetime.now(datetime.timezone.utc) - created_dt).total_seconds()
                    if age_seconds > self.max_command_age_seconds:
                        error_msg = f"Command #{cmd_id} expired: age is {int(age_seconds)}s (max allowed: {self.max_command_age_seconds}s)"
                        logger.warning(error_msg)
                        self._report_result(cmd_id, status="failed", output=error_msg)
                        return
            except Exception as e:
                logger.debug(f"Could not parse created_at timestamp for command #{cmd_id}: {e}")

        # 3. Schema and allowlist validation
        try:
            validated_params = parse_and_validate_command_parameters(action_name, raw_params)
        except ValueError as ve:
            error_msg = f"Security / schema validation failed: {ve}"
            logger.error(f"Command #{cmd_id} rejected: {error_msg}")
            self._report_result(cmd_id, status="failed", output=error_msg)
            return

        # 3. Execution
        exec_res = self._execute_action(action_name, validated_params, is_sim)

        # 4. Optional Post-Execution Verification
        final_output = exec_res.output
        if exec_res.success and action_name == "restart_service" and isinstance(validated_params, RestartServiceParams):
            verified, v_msg = CommandVerifier.verify_service_running(validated_params, simulation=is_sim)
            final_output = f"{final_output}\nVerification: {v_msg}"
            if not verified:
                exec_res.status = "failed"
                exec_res.success = False

        # 5. Report execution result to backend
        self._report_result(cmd_id, status=exec_res.status, output=final_output)

    def _execute_action(
        self,
        action_name: str,
        params: Any,
        simulation: bool
    ) -> ExecutionResult:
        """Route to appropriate safe execution handler."""
        try:
            if action_name == "restart_service" and isinstance(params, RestartServiceParams):
                return CommandExecutor.execute_restart_service(params, simulation=simulation)
            elif action_name == "restart_servicepulse_agent" and isinstance(params, RestartAgentParams):
                return CommandExecutor.execute_restart_agent(params, simulation=simulation)
            elif action_name == "run_diagnostic_check" and isinstance(params, DiagnosticCheckParams):
                return CommandExecutor.execute_diagnostic_check(params, simulation=simulation)
            elif action_name == "recheck_network_endpoint" and isinstance(params, RecheckNetworkParams):
                return CommandExecutor.execute_recheck_network(params, simulation=simulation)
            elif action_name == "notify_administrator" and isinstance(params, NotifyAdminParams):
                return CommandExecutor.execute_notify_admin(params, simulation=simulation)
            elif action_name == "install_approved_software" and isinstance(params, InstallApprovedSoftwareParams):
                return CommandExecutor.execute_install_approved_software(params, simulation=simulation)
            else:
                return ExecutionResult(
                    success=False,
                    status="failed",
                    output=f"Unrecognized or mismatched action: {action_name}"
                )
        except Exception as e:
            logger.error(f"Unexpected error executing action '{action_name}': {e}")
            return ExecutionResult(
                success=False,
                status="failed",
                output=f"Execution exception: {e}"
            )

    def _report_result(self, cmd_id: int, status: str, output: str) -> None:
        """Submit command result to backend."""
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            self.api_client.report_command_result(
                command_id=cmd_id,
                status=status,
                execution_result=output,
                executed_at=now_str
            )
            logger.info(f"Command #{cmd_id} execution result '{status}' submitted to backend.")
        except Exception as e:
            logger.error(f"Failed to submit execution result for command #{cmd_id}: {e}")
