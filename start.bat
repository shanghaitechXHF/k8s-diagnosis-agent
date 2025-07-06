@echo off
echo ================================
echo K8s Diagnosis Agent - Windows启动脚本
echo ================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)

REM 检查是否安装了依赖
if not exist "k8s_diagnosis_agent" (
    echo ❌ 项目目录不存在
    pause
    exit /b 1
)

REM 检查配置文件
if not exist ".env" (
    echo ⚠️ .env文件不存在，从示例创建...
    if exist "env.example" (
        copy env.example .env >nul
        echo 📝 请编辑.env文件配置API密钥
    ) else (
        echo ❌ env.example文件不存在
        pause
        exit /b 1
    )
)

REM 安装依赖（如果需要）
echo 📦 检查并安装依赖...
pip install -r requirements.txt >nul 2>&1
pip install -e . >nul 2>&1

echo 🚀 启动 K8s Diagnosis Agent...
echo.
echo 选择运行模式:
echo 1. Web服务模式 (推荐)
echo 2. 交互式模式
echo 3. 退出
echo.
set /p choice=请选择 (1-3): 

if "%choice%"=="1" (
    echo.
    echo 🌐 启动Web服务...
    echo 📍 访问地址: http://localhost:8000
    echo 📚 API文档: http://localhost:8000/docs
    echo.
    python -m k8s_diagnosis_agent --mode web
) else if "%choice%"=="2" (
    echo.
    echo 💬 启动交互式模式...
    echo.
    python -m k8s_diagnosis_agent --mode interactive
) else if "%choice%"=="3" (
    echo 再见!
    exit /b 0
) else (
    echo ❌ 无效选择
    pause
    goto start
)

pause 