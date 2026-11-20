"""
ServicePulse - Primary Platform Owner Bootstrap Wrapper Script
Executes `backend.app.cli.bootstrap_owner`.
"""
import asyncio
from backend.app.cli.bootstrap_owner import main

if __name__ == "__main__":
    asyncio.run(main())
