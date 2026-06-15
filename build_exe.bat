@echo off
REM ADXRay Game Spy - PyInstaller 打包脚本
REM 需要先安装: pip install pyinstaller

chcp 65001 >nul

echo ========================================
echo  ADXRay Game Spy - 打包脚本
echo ========================================
echo.

REM 安装依赖
echo [1/4] 检查依赖...
pip install playwright pyinstaller --quiet
echo.

REM 安装浏览器
echo [2/4] 安装 Playwright 浏览器...
python -m playwright install chromium
echo.

REM 清理旧的构建
echo [3/4] 清理旧构建...
if exist "dist\adxray-spy" rmdir /s /q "dist\adxray-spy"
if exist "build" rmdir /s /q "build"
if exist "adxray-spy.spec" del "adxray-spy.spec"
echo.

REM PyInstaller 打包
echo [4/4] 打包中...
pyinstaller --onefile ^
    --name "adxray-spy" ^
    --windowed ^
    --icon NONE ^
    --add-data "README.md;." ^
    --hidden-import playwright ^
    --hidden-import adxray_spy_core ^
    "adxray_spy_gui.py"

echo.
echo ========================================
if exist "dist\adxray-spy.exe" (
    echo 打包成功！
    echo 输出: dist\adxray-spy.exe
    echo 大小:
    dir "dist\adxray-spy.exe"
) else (
    echo 打包失败，请检查错误信息
)
echo ========================================
pause
