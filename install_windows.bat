@echo off
chcp 65001 >nul
title Union·由你 CNC AI 工艺大脑 v11.0.2 — 一键安装
cd /d %~dp0

echo.
echo ═══════════════════════════════════════════════════════
echo   Union·由你 — CNC AI 工艺大脑 v11.0.2
echo   一键安装脚本 (Windows)
echo ═══════════════════════════════════════════════════════
echo.

:: ── 步骤1: 检测 Python ──
echo [1/5] 检测 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未找到 Python, 请先安装 Python 3.10+
    echo   下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo    [OK]

:: ── 步骤2: 安装/检测 Ollama ──
echo.
echo [2/5] 检测 Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo   Ollama 未安装, 正在下载...
    curl -L -o ollama-install.exe https://ollama.com/download/OllamaSetup.exe
    if %errorlevel% neq 0 (
        echo   [警告] 自动下载失败, 请手动安装:
        echo   https://ollama.com/download/windows
    ) else (
        echo   正在安装 Ollama (请在弹出的安装窗口中完成)...
        start /wait ollama-install.exe
        del ollama-install.exe
    )
) else (
    ollama --version
    echo    [OK]
)

:: ── 步骤3: 拉取模型 ──
echo.
echo [3/5] 拉取 AI 模型 (qwen2.5:3b, ~2GB)...
echo   这可能需要几分钟, 取决于网速...
ollama pull qwen2.5:3b
if %errorlevel% neq 0 (
    echo   [警告] 模型拉取失败, 确认 Ollama 正在运行
    echo   运行: start ollama serve
)
echo    [OK]

:: ── 步骤4: 安装 Python 依赖 ──
echo.
echo [4/5] 安装 Python 依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
if %errorlevel% neq 0 (
    echo   [错误] 依赖安装失败
    pause
    exit /b 1
)
echo    [OK]

:: ── 步骤5: 启动服务 ──
echo.
echo [5/5] 启动 CNC AI 工艺大脑...
echo.
echo ═══════════════════════════════════════════════════════
echo   服务已启动!
echo   浏览器打开: http://localhost:7861
echo   仪表盘:     http://localhost:7861/api/dashboard
echo   演示:       http://localhost:7861/api/demo
echo ═══════════════════════════════════════════════════════
echo.
echo 按 Ctrl+C 停止服务
echo.
python app/main.py

pause
