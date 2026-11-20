#!/usr/bin/env python3
"""
ServicePulse Native Windows Agent - Root CLI Entrypoint
Author: Muhammadyusuf Usmonov
"""
import os
import sys

# Ensure 'agent' directory is in Python path when executed directly
agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from servicepulse.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
