#!/bin/bash

# K8s Diagnosis Agent 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查依赖
check_dependencies() {
    print_message $BLUE "🔍 检查依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_message $RED "❌ Python3 未安装"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip &> /dev/null; then
        print_message $RED "❌ pip 未安装"
        exit 1
    fi
    
    print_message $GREEN "✅ 依赖检查通过"
}

# 安装依赖
install_dependencies() {
    print_message $BLUE "📦 安装依赖..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        print_message $RED "❌ requirements.txt 文件不存在"
        exit 1
    fi
    
    # 安装项目
    pip install -e .
    
    print_message $GREEN "✅ 依赖安装完成"
}

# 检查配置
check_config() {
    print_message $BLUE "⚙️ 检查配置..."
    
    if [ ! -f ".env" ]; then
        print_message $YELLOW "⚠️ .env 文件不存在，将从示例创建"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_message $YELLOW "📝 请编辑 .env 文件配置 API 密钥"
        else
            print_message $RED "❌ .env.example 文件不存在"
            exit 1
        fi
    fi
    
    print_message $GREEN "✅ 配置检查完成"
}

# 检查Kubernetes连接
check_k8s() {
    print_message $BLUE "🔧 检查Kubernetes连接..."
    
    if command -v kubectl &> /dev/null; then
        if kubectl cluster-info &> /dev/null; then
            print_message $GREEN "✅ Kubernetes 集群连接正常"
        else
            print_message $YELLOW "⚠️ 无法连接到Kubernetes集群"
            print_message $YELLOW "   请确保 kubeconfig 配置正确"
        fi
    else
        print_message $YELLOW "⚠️ kubectl 未安装，跳过K8s连接检查"
    fi
}

# 启动应用
start_app() {
    local mode=${1:-web}
    local host=${2:-0.0.0.0}
    local port=${3:-8000}
    
    print_message $BLUE "🚀 启动 K8s Diagnosis Agent..."
    print_message $BLUE "   模式: $mode"
    print_message $BLUE "   地址: $host:$port"
    
    case $mode in
        web)
            print_message $GREEN "🌐 Web服务启动中..."
            print_message $GREEN "📍 访问地址: http://$host:$port"
            print_message $GREEN "📚 API文档: http://$host:$port/docs"
            python -m k8s_diagnosis_agent --mode web --host "$host" --port "$port"
            ;;
        interactive)
            print_message $GREEN "💬 交互式模式启动中..."
            python -m k8s_diagnosis_agent --mode interactive
            ;;
        *)
            print_message $RED "❌ 不支持的模式: $mode"
            print_message $BLUE "支持的模式: web, interactive"
            exit 1
            ;;
    esac
}

# 显示帮助
show_help() {
    echo "K8s Diagnosis Agent 启动脚本"
    echo ""
    echo "用法: $0 [选项] [模式] [主机] [端口]"
    echo ""
    echo "选项:"
    echo "  --install-deps    安装依赖"
    echo "  --check-only      仅检查环境，不启动"
    echo "  --help           显示帮助"
    echo ""
    echo "模式:"
    echo "  web              Web服务模式 (默认)"
    echo "  interactive      交互式模式"
    echo ""
    echo "示例:"
    echo "  $0                           # 启动Web服务 (默认端口8000)"
    echo "  $0 web 0.0.0.0 8080        # 启动Web服务在8080端口"
    echo "  $0 interactive              # 启动交互式模式"
    echo "  $0 --install-deps           # 安装依赖"
    echo "  $0 --check-only             # 仅检查环境"
}

# 主函数
main() {
    print_message $BLUE "🔧 K8s Diagnosis Agent 启动脚本"
    print_message $BLUE "================================"
    
    # 解析参数
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --install-deps)
            check_dependencies
            install_dependencies
            exit 0
            ;;
        --check-only)
            check_dependencies
            check_config
            check_k8s
            print_message $GREEN "✅ 环境检查完成"
            exit 0
            ;;
        *)
            # 正常启动流程
            check_dependencies
            check_config
            check_k8s
            
            # 启动应用
            mode=${1:-web}
            host=${2:-0.0.0.0}
            port=${3:-8000}
            
            start_app "$mode" "$host" "$port"
            ;;
    esac
}

# 运行主函数
main "$@" 