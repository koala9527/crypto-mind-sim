@echo off
echo ========================================
echo CryptoMindSim - 数据库清理工具
echo ========================================
echo.
echo 警告：此操作将删除数据库文件！
echo 请先停止运行中的应用（按 Ctrl+C）
echo.
pause

cd /d "%~dp0\.."

echo.
echo 正在删除数据库文件...
if exist neotrade.db (
    del /F neotrade.db
    if exist neotrade.db (
        echo [错误] 无法删除数据库文件，文件可能正在被使用
        echo 请先停止应用，然后重新运行此脚本
        pause
        exit /b 1
    ) else (
        echo [成功] 数据库文件已删除
    )
) else (
    echo [提示] 数据库文件不存在
)

echo.
echo 正在重新创建数据库...
.venv\Scripts\python.exe -m backend.utils.reset_db --force

echo.
echo ========================================
echo 完成！
echo ========================================
pause
