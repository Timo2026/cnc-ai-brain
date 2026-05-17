# -*- mode: python ; coding: utf-8 -*-
"""
🦞 Union·由你 CNC AI 工艺大脑 — PyInstaller 打包规格
Windows EXE 打包: pyinstaller union_by_ni.spec
输出: dist/union_cnc_brain.exe

注意:
- Ollama 必须单独安装并运行 (https://ollama.com)
- 模型: qwen2.5:3b (ollama pull qwen2.5:3b)
"""

import sys
from pathlib import Path

block_cipher = None

import os
# 项目根目录
PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(SPECPATH))).parent
if not (PROJECT_ROOT / 'app' / 'main.py').exists():
    # PyInstaller 6.x: SPECPATH 可能只是文件名，从 CWD 推导
    PROJECT_ROOT = Path(os.getcwd())

# 收集所有 Python 源文件
a = Analysis(
    [str(PROJECT_ROOT / 'app' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # 配置文件
        (str(PROJECT_ROOT / 'config' / 'experts'), 'config/experts'),
        (str(PROJECT_ROOT / 'config' / 'skills'), 'config/skills'),
        # 数据目录（空目录占位）
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'starlette',
        'starlette.routing',
        'anyio',
        'sqlite3',
        'json',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
    ],
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
    name='union_cnc_brain',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 控制台窗口（方便调试）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可替换为 .ico 文件路径
)
