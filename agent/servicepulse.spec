# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for ServicePulse Windows Agent
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden_imports = [
    'servicepulse',
    'servicepulse.agent',
    'servicepulse.config',
    'servicepulse.authentication',
    'servicepulse.enrollment',
    'servicepulse.api_client',
    'servicepulse.telemetry',
    'servicepulse.collectors',
    'servicepulse.collectors.system',
    'servicepulse.collectors.windows_activation',
    'servicepulse.collectors.defender',
    'servicepulse.collectors.network',
    'servicepulse.queue',
    'servicepulse.queue.storage',
    'servicepulse.queue.sync',
    'servicepulse.commands',
    'servicepulse.commands.allowlist',
    'servicepulse.commands.schemas',
    'servicepulse.commands.execution',
    'servicepulse.commands.verification',
    'servicepulse.commands.dispatcher',
    'servicepulse.service',
    'servicepulse.service.windows_service',
    'servicepulse.service.installer',
    'servicepulse.logging',
    'servicepulse.logging.setup',
    'psutil',
    'pydantic',
    'httpx',
    'sqlite3',
]

if sys.platform == 'win32':
    hidden_imports.extend([
        'win32service',
        'win32serviceutil',
        'win32event',
        'win32crypt',
        'servicemanager',
    ])

a = Analysis(
    ['servicepulse_agent.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.example.json', '.'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ServicePulseAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
