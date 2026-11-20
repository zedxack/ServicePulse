"""
ServicePulse Windows Agent - Build & Packaging Script
Packages the Python agent into a standalone ServicePulseAgent.exe binary using PyInstaller.
Author: Muhammadyusuf Usmonov
"""
import os
import subprocess
import sys
from pathlib import Path


def build_binary() -> int:
    """Build standalone executable."""
    agent_dir = Path(__file__).resolve().parent
    spec_path = agent_dir / "servicepulse.spec"

    print("=================================================================")
    print("ServicePulse Native Windows Agent - Standalone Executable Build")
    print("Author: Muhammadyusuf Usmonov")
    print(f"Target OS: Windows 11 x64 / Python {sys.version.split()[0]}")
    print("=================================================================")

    if not spec_path.exists():
        print(f"ERROR: Spec file {spec_path} not found.")
        return 1

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path),
    ]

    print(f"Executing: {' '.join(cmd)}")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(agent_dir)

    result = subprocess.run(cmd, cwd=str(agent_dir), env=env, check=False)
    if result.returncode == 0:
        dist_exe = agent_dir / "dist" / "ServicePulseAgent.exe"
        if dist_exe.exists():
            size_mb = round(dist_exe.stat().st_size / (1024 * 1024), 2)
            print("=================================================================")
            print(f"SUCCESS: Packaged standalone binary created: {dist_exe} ({size_mb} MB)")
            print("=================================================================")
            return 0
        else:
            print("WARNING: PyInstaller returned 0 but executable not found in dist/")
            return 1
    else:
        print(f"ERROR: PyInstaller build failed with exit code {result.returncode}")
        return result.returncode


if __name__ == "__main__":
    sys.exit(build_binary())
