@echo off
chcp 65001 >nul
title Union·由你 CNC AI 工艺大脑 v11.0.4 Full — 一键安装
cd /d %~dp0

echo.
echo ═══════════════════════════════════════════════════════
echo   Union·由你 — CNC AI 工艺大脑 v11.0.4 Full
echo   一键安装脚本 (Windows)
echo   支持: 本地Ollama / 云端DeepSeek/GLM/通义
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

:: ── 步骤2: 配置模型 ──
echo.
echo [2/5] 模型配置...
echo   模式1: 本地Ollama (自动检测, 无需配置)
echo   模式2: 云端API (编辑 config\models.json 添加API key)
if exist "config\models.json" (
    echo   配置文件: config\models.json [已存在]
) else (
    echo   [创建默认配置]
)
echo    [OK]

:: ── 步骤3: 安装 Python 依赖 ──
echo.
echo [3/5] 安装 Python 依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
if %errorlevel% neq 0 (
    echo   [错误] 依赖安装失败
    pause
    exit /b 1
)
echo    [OK]

:: ── 步骤4: 服务启动 ──
echo.
echo [4/5] 启动 Union·由你 v11.0.4...
echo.
echo ═══════════════════════════════════════════════════════
echo   服务启动中...
echo   浏览器打开: http://localhost:7861
echo   模型状态:   http://localhost:7861/api/models
echo   仪表盘:     http://localhost:7861/api/dashboard
echo ═══════════════════════════════════════════════════════
echo.
echo 按 Ctrl+C 停止服务
echo.
python app/main.py

pause
