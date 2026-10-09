@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo E报销助手_f24016137
echo 启动后请在浏览器访问 http://127.0.0.1:5000
echo 请保持本窗口打开，按 Ctrl+C 停止服务。
python run.py
pause
