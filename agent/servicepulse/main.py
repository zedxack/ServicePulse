"""
ServicePulse Native Windows Agent - CLI Application Controller
Dispatches CLI arguments for enrollment, console execution, and service operations.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import argparse
import sys
from pathlib import Path

from servicepulse import __author__, __version__
from servicepulse.agent import ServicePulseAgent
from servicepulse.authentication import CredentialStore
from servicepulse.config import AgentConfig
from servicepulse.enrollment import EnrollmentManager
from servicepulse.logging.setup import get_logger, setup_logging
from servicepulse.service.installer import ServiceManager

logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="servicepulse-agent",
        description=f"ServicePulse Native Windows Agent v{__version__} by {__author__}",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Run agent in foreground console mode for development/debugging."
    )
    parser.add_argument(
        "--enroll",
        action="store_true",
        help="Enroll agent against ServicePulse backend using pre-shared secret."
    )
    parser.add_argument(
        "--secret",
        type=str,
        default=None,
        help="Pre-shared enrollment secret for authentication."
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default=None,
        help="Override backend server URL for enrollment (e.g. http://localhost:8000)."
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=None,
        help="Optional pre-existing Device ID to bind to."
    )
    parser.add_argument(
        "--org-id",
        type=int,
        default=None,
        help="Optional Organization ID for tenant scoping."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom JSON configuration file."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install ServicePulse as a Windows Service (Administrator required)."
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start the ServicePulse Windows Service."
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the ServicePulse Windows Service."
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Restart the ServicePulse Windows Service."
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall the ServicePulse Windows Service (Administrator required)."
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Query agent enrollment status and Windows Service state."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ServicePulse Agent {__version__}"
    )
    return parser


def main() -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    # Configure logging
    config_path = Path(args.config) if args.config else None
    config = AgentConfig.load(config_path)

    if args.server_url:
        config.server_url = args.server_url

    setup_logging(level=config.log_level, console=True)

    # 1. Enrollment
    if args.enroll:
        if not args.secret:
            print("ERROR: --secret is required when enrolling an agent.")
            return 1
        try:
            creds = EnrollmentManager.enroll_agent(
                config=config,
                enrollment_secret=args.secret,
                device_id=args.device_id,
                organization_id=args.org_id,
            )
            print("SUCCESS: Agent enrolled successfully!")
            print(f"Agent UUID: {creds.agent_uuid}")
            print(f"Device ID: {creds.device_id}")
            print(f"Credentials protected by Windows DPAPI: {config.get_credentials_path()}")
            return 0
        except Exception as e:
            print(f"ERROR: Enrollment failed: {e}")
            return 1

    # 2. Service Management Commands
    if args.install:
        success = ServiceManager.install_service()
        return 0 if success else 1

    if args.start:
        success = ServiceManager.start_service()
        return 0 if success else 1

    if args.stop:
        success = ServiceManager.stop_service()
        return 0 if success else 1

    if args.restart:
        success = ServiceManager.restart_service()
        return 0 if success else 1

    if args.uninstall:
        success = ServiceManager.uninstall_service()
        return 0 if success else 1

    # 3. Status Query
    if args.status:
        cred_store = CredentialStore(config.get_credentials_path())
        has_creds = cred_store.has_credentials()
        creds = cred_store.load_credentials() if has_creds else None
        svc_status = ServiceManager.get_service_status()

        print("=== ServicePulse Windows Agent Status ===")
        print(f"Agent Version:     {__version__}")
        print(f"Configured Server: {config.server_url}")
        print(f"Agent Name:        {config.agent_name}")
        print(f"Enrolled:          {'YES' if creds else 'NO'}")
        if creds:
            print(f"Agent UUID:        {creds.agent_uuid}")
            print(f"Bound Device ID:   {creds.device_id}")
            print(f"Organization ID:   {creds.organization_id}")
        print(f"Windows Service:   {svc_status.get('status', 'unknown').upper()}")
        print(f"Service Installed: {svc_status.get('installed', 'unknown')}")
        print(f"Queue DB Path:     {config.get_queue_db_path()}")
        return 0

    # 4. Console execution
    if args.console:
        print("Starting ServicePulse Agent in foreground console mode...")
        print(f"Server: {config.server_url}")
        print("Press Ctrl+C to terminate.")
        agent = ServicePulseAgent(config)
        try:
            agent.run()
            return 0
        except KeyboardInterrupt:
            print("\nShutting down ServicePulse Agent...")
            agent.stop()
            return 0

    # If run on Windows without arguments, check if launched as a Windows Service
    if sys.platform == "win32":
        try:
            import servicemanager

            from servicepulse.service.windows_service import ServicePulseWindowsService

            # Try to start service dispatcher
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(ServicePulseWindowsService)
            servicemanager.StartServiceCtrlDispatcher()
            return 0
        except Exception:
            # Not started by SCM, show help
            parser.print_help()
            return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
