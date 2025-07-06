#!/bin/bash

# 多版本Docker镜像构建脚本
set -e

# 配置
REGISTRY="k8s-diagnosis-agent"
VERSION="0.1.0"
PLATFORMS="linux/amd64,linux/arm64"
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12")

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和buildx
check_prerequisites() {
    print_info "检查构建环境..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        exit 1
    fi
    
    if ! docker buildx version &> /dev/null; then
        print_error "Docker buildx未安装"
        exit 1
    fi
    
    print_info "构建环境检查通过"
}

# 创建buildx builder
create_builder() {
    print_info "创建buildx builder..."
    
    if ! docker buildx ls | grep -q "k8s-diagnosis-builder"; then
        docker buildx create --name k8s-diagnosis-builder --use
    else
        docker buildx use k8s-diagnosis-builder
    fi
    
    docker buildx inspect --bootstrap
}

# 生成特定版本的Dockerfile
generate_dockerfile() {
    local python_version=$1
    local dockerfile_name="Dockerfile.python${python_version//.}"
    
    print_info "生成 ${dockerfile_name}..."
    
    cat > ${dockerfile_name} << EOF
# Python ${python_version}版本Dockerfile
FROM python:${python_version}-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1 \\
    PYTHON_VERSION=${python_version}

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    openssh-client \\
    procps \\
    net-tools \\
    iputils-ping \\
    dnsutils \\
    telnet \\
    vim \\
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --upgrade pip

# 复制requirements文件
COPY requirements/python${python_version//.}.txt requirements.txt

# 安装Python依赖
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app && \\
    chown -R app:app /app

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/config /app/ssh /app/kubeconfig && \\
    chown -R app:app /app/data /app/logs /app/config /app/ssh /app/kubeconfig

# 切换到非root用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["python", "-m", "k8s_diagnosis_agent", "--mode", "web"]
EOF
}

# 构建镜像
build_image() {
    local python_version=$1
    local dockerfile_name="Dockerfile.python${python_version//.}"
    local image_tag="${REGISTRY}:${VERSION}-python${python_version}"
    local latest_tag="${REGISTRY}:latest-python${python_version}"
    
    print_info "构建 Python ${python_version} 镜像..."
    
    # 生成Dockerfile
    generate_dockerfile ${python_version}
    
    # 构建多架构镜像
    docker buildx build \
        --file ${dockerfile_name} \
        --platform ${PLATFORMS} \
        --tag ${image_tag} \
        --tag ${latest_tag} \
        --push \
        .
    
    print_info "Python ${python_version} 镜像构建完成"
}

# 构建所有版本
build_all_versions() {
    print_info "开始构建所有版本..."
    
    for version in "${PYTHON_VERSIONS[@]}"; do
        build_image ${version}
    done
}

# 构建manifest
build_manifest() {
    print_info "创建multi-arch manifest..."
    
    # 创建版本manifest
    local manifest_tags=()
    for version in "${PYTHON_VERSIONS[@]}"; do
        manifest_tags+=("${REGISTRY}:${VERSION}-python${version}")
    done
    
    # 创建主manifest
    docker buildx imagetools create \
        --tag ${REGISTRY}:${VERSION} \
        --tag ${REGISTRY}:latest \
        "${manifest_tags[@]}"
    
    print_info "Manifest创建完成"
}

# 测试镜像
test_images() {
    print_info "测试镜像..."
    
    for version in "${PYTHON_VERSIONS[@]}"; do
        local image_tag="${REGISTRY}:${VERSION}-python${version}"
        print_info "测试 ${image_tag}..."
        
        # 运行容器测试
        docker run --rm ${image_tag} python --version
        
        # 检查健康检查
        local container_id=$(docker run -d -p 8000:8000 ${image_tag})
        sleep 10
        
        if curl -f http://localhost:8000/api/v1/health; then
            print_info "Python ${version} 镜像健康检查通过"
        else
            print_warn "Python ${version} 镜像健康检查失败"
        fi
        
        docker stop ${container_id}
    done
}

# 清理临时文件
cleanup() {
    print_info "清理临时文件..."
    
    for version in "${PYTHON_VERSIONS[@]}"; do
        local dockerfile_name="Dockerfile.python${version//.}"
        rm -f ${dockerfile_name}
    done
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -v, --version       设置版本号 (默认: ${VERSION})"
    echo "  -r, --registry      设置镜像仓库 (默认: ${REGISTRY})"
    echo "  -p, --platforms     设置构建平台 (默认: ${PLATFORMS})"
    echo "  --python-versions   设置Python版本 (默认: ${PYTHON_VERSIONS[*]})"
    echo "  --no-test          跳过镜像测试"
    echo "  --no-push          不推送镜像"
    echo ""
    echo "示例:"
    echo "  $0 -v 1.0.0 -r myregistry/k8s-diagnosis-agent"
    echo "  $0 --python-versions \"3.9 3.11\""
}

# 主函数
main() {
    local skip_test=false
    local skip_push=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -p|--platforms)
                PLATFORMS="$2"
                shift 2
                ;;
            --python-versions)
                IFS=' ' read -ra PYTHON_VERSIONS <<< "$2"
                shift 2
                ;;
            --no-test)
                skip_test=true
                shift
                ;;
            --no-push)
                skip_push=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_info "开始构建K8s诊断Agent多版本镜像..."
    print_info "版本: ${VERSION}"
    print_info "仓库: ${REGISTRY}"
    print_info "平台: ${PLATFORMS}"
    print_info "Python版本: ${PYTHON_VERSIONS[*]}"
    
    # 执行构建流程
    check_prerequisites
    create_builder
    build_all_versions
    
    if [[ "$skip_push" == false ]]; then
        build_manifest
    fi
    
    if [[ "$skip_test" == false ]]; then
        test_images
    fi
    
    cleanup
    
    print_info "构建完成！"
}

# 错误处理
trap 'print_error "构建失败！"; cleanup; exit 1' ERR

# 运行主函数
main "$@" 