"""
ServicePulse - Automated Remediation Policy Engine
Enforces strict action allowlisting, parameter schema validation, cooldown periods,
maximum retry limits, and authorization/approval requirements.
Author: Muhammadyusuf Usmonov
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.inventory import Device
from backend.app.models.remediation import RemediationExecution, RemediationRule
from backend.app.schemas.remediation import (
    NotifyAdminParams,
    RecheckNetworkParams,
    RestartAgentParams,
    RestartServiceParams,
    RunDiagnosticParams,
)


class RemediationPolicy:
    """
    Validates remediation rules, action allowlists, and execution constraints.
    Prevents shell injection and unauthorized command execution.
    """

    ALLOWED_ACTIONS = {
        "restart_service": RestartServiceParams,
        "restart_servicepulse_agent": RestartAgentParams,
        "run_diagnostic_check": RunDiagnosticParams,
        "recheck_network_endpoint": RecheckNetworkParams,
        "notify_administrator": NotifyAdminParams,
    }

    @classmethod
    def validate_action(cls, action_name: str, action_params_raw: Optional[str]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate that action is strictly allowlisted and parameters conform to schema.
        Returns: (is_valid, error_message, validated_params_dict)
        """
        if action_name not in cls.ALLOWED_ACTIONS:
            return False, f"Action '{action_name}' is not in the allowlist. Allowed: {list(cls.ALLOWED_ACTIONS.keys())}", None

        param_schema = cls.ALLOWED_ACTIONS[action_name]
        try:
            if action_params_raw:
                try:
                    data = json.loads(action_params_raw)
                except Exception:
                    # Treat single string as service_name if applicable
                    if action_name == "restart_service":
                        data = {"service_name": action_params_raw.strip()}
                    else:
                        return False, "Action parameters must be valid JSON", None
            else:
                data = {}

            # If action is restart_service and no service_name given, default to ServicePulseAgent
            if action_name == "restart_service" and "service_name" not in data:
                data["service_name"] = "ServicePulseAgent"

            model_inst = param_schema(**data)
            return True, None, model_inst.model_dump()

        except ValidationError as ve:
            return False, f"Parameter validation failed for '{action_name}': {str(ve)}", None
        except Exception as e:
            return False, f"Action validation error: {str(e)}", None

    @classmethod
    async def check_execution_eligibility(
        cls,
        rule: RemediationRule,
        device: Optional[Device],
        db: AsyncSession
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if remediation rule is eligible to execute:
        1. Rule is active.
        2. Device type matches target_device_type (if specified).
        3. Cooldown period has elapsed since last execution for this rule and device.
        4. Max retry limit has not been exceeded.
        """
        if not rule.is_active:
            return False, f"Remediation rule '{rule.name}' is inactive"

        if device and rule.target_device_type:
            if device.device_type != rule.target_device_type:
                return False, f"Device type '{device.device_type}' does not match rule target '{rule.target_device_type}'"

        now = datetime.now(timezone.utc)

        # Check cooldown and recent executions
        if device:
            recent_q = (
                select(RemediationExecution)
                .where(
                    RemediationExecution.rule_id == rule.id,
                    RemediationExecution.device_id == device.id,
                )
                .order_by(RemediationExecution.created_at.desc())
                .limit(1)
            )
            last_exec = (await db.execute(recent_q)).scalar_one_or_none()

            if last_exec:
                cooldown_delta = timedelta(seconds=rule.cooldown_seconds or settings.REMEDIATION_COOLDOWN_SECONDS)
                if (now - last_exec.created_at) < cooldown_delta and last_exec.status not in ("rejected", "failed"):
                    return False, f"Rule '{rule.name}' is in cooldown for device {device.name} (cooldown: {rule.cooldown_seconds}s)"

                # Check retries for current incident
                if last_exec.status == "failure" and last_exec.retry_count >= rule.max_retries:
                    return False, f"Rule '{rule.name}' has exceeded max retries ({rule.max_retries}) for device {device.name}"

        return True, None
