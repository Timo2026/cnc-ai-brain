@echo off
chcp 65001 >nul
title Union·由你 CNC AI 工艺大脑 v11.0.5 Full — 一键安装
cd /d %~dp0

echo.
echo ═══════════════════════════════════════════════════════
echo   Union·由你 — CNC AI 工艺大脑 v11.0.5 Full
echo   一键安装脚本 (Windows)
echo   支持: 本地Ollama / 云端DeepSeek/GLM/通义
echo ═══════════════════════════════════════════════════════
echo.

:: ── 0: 检测管理员权限 ──
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo   [提示] 建议以管理员权限运行
    echo   右键 install_windows.bat → 以管理员身份运行
    echo   继续安装到用户目录...
    echo.
)

:: ── 步骤1: 检测 Python ──
echo [1/5] 检测 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未找到 Python 3.10+
    echo   下载: https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo    [OK]

:: ── 步骤2: 检测 Ollama ──
echo.
echo [2/5] 检测 Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   Ollama 未安装, 正在下载...
    echo   下载链接: https://ollama.com/download/windows
    echo   安装后打开 Ollama, 运行: ollama pull qwen2.5:3b
    echo.
    echo   没有Ollama也不影响基础功能(画图+报价+预览)
    echo   只需确保 config\models.json 中配置了云端API或跳过
) else (
    ollama --version
    echo   检查模型...
    ollama list | findstr "qwen2.5:3b" >nul
    if %errorlevel% neq 0 (
        echo   正在下载 qwen2.5:3b (~2GB, 取决于网速)...
        ollama pull qwen2.5:3b
    ) else (
        echo   模型已就绪
    )
)
echo    [OK]

:: ── 步骤3: 安装 Python 依赖 ──
echo.
echo [3/5] 安装 Python 依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
if %errorlevel% neq 0 (
    echo   [警告] pip安装失败, 重试中...
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo   [错误] 依赖安装失败, 请手动运行:
        echo   pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo    [OK]

:: ── 步骤4: 安装 OCC (可选, 精确STEP) ──
echo.
echo [4/5] 检测 OCC 引擎 (可选, 精确B-Rep STEP导出)...
python -c "import OCC.Core" >nul 2>&1
if %errorlevel% neq 0 (
    echo   OCC未安装, 自动降级trimesh引擎(三角网格,预览用)
    echo   如需精确STEP, 运行:
    echo   conda install -c conda-forge pythonocc-core
    echo   或使用 install_windows_full.bat (完整离线版)
) else (
    echo   OCC引擎已就绪 — 生成B-Rep精确STEP
)
echo    [OK]

:: ── 步骤5: 检测端口 + 启动服务 ──
echo.
echo [5/5] 检测端口并启动服务...
set PORT=7861
:check_port
netstat -ano | findstr ":%PORT% " >nul 2>&1
if %errorlevel% equ 0 (
    set /a PORT=PORT+1
    if %PORT% gtr 7870 (
        echo   [错误] 7861-7870端口全被占用
        pause
        exit /b 1
    )
    goto check_port
)
echo   端口 %PORT% 可用
echo.
echo ═══════════════════════════════════════════════════════
echo   安装完成! 服务启动中...
echo   浏览器打开: http://localhost:%PORT%
echo   模型状态:   http://localhost:%PORT%/api/models
echo   仪表盘:     http://localhost:%PORT%/api/dashboard
echo ═══════════════════════════════════════════════════════
echo.
echo 按 Ctrl+C 停止服务
echo.
python app/main.py --port %PORT%

pause
