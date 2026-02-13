@echo off
echo ========================================
echo CryptoMindSim - 数据库清理工具
echo ========================================
echo.
echo 警告：此操作将重置数据库！
echo 请先停止运行中的应用（按 Ctrl+C）
echo.
pause

cd /d "%~dp0\.."

echo.
echo 正在重置数据库...
.venv\Scripts\python.exe -m backend.utils.reset_db --force

echo.
echo ========================================
echo 完成！
echo ========================================
pause
