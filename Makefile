.PHONY: help install dev test clean build docker run-web run-interactive

# 默认目标
help:
	@echo "K8s Diagnosis Agent - Makefile"
	@echo "=============================="
	@echo ""
	@echo "可用命令:"
	@echo "  install         安装依赖"
	@echo "  dev             开发环境安装"
	@echo "  test            运行测试"
	@echo "  clean           清理文件"
	@echo "  build           构建项目"
	@echo "  docker          构建Docker镜像"
	@echo "  run-web         启动Web服务"
	@echo "  run-interactive 启动交互式模式"
	@echo "  format          格式化代码"
	@echo "  lint            代码检查"

# 安装依赖
install:
	pip install -r requirements.txt
	pip install -e .

# 开发环境
dev:
	pip install -r requirements.txt
	pip install -e .[dev]

# 运行测试
test:
	pytest tests/ -v

# 清理文件
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# 构建项目
build:
	python -m build

# 构建Docker镜像
docker:
	docker build -t k8s-diagnosis-agent .

# 运行Docker容器
docker-run:
	docker run -p 8000:8000 \
		-v ${HOME}/.kube:/root/.kube:ro \
		-e OPENAI_API_KEY=${OPENAI_API_KEY} \
		-e CLAUDE_API_KEY=${CLAUDE_API_KEY} \
		-e DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY} \
		k8s-diagnosis-agent

# 使用docker-compose启动
docker-compose:
	docker-compose up --build

# 启动Web服务
run-web:
	python -m k8s_diagnosis_agent --mode web

# 启动交互式模式
run-interactive:
	python -m k8s_diagnosis_agent --mode interactive

# 代码格式化
format:
	black k8s_diagnosis_agent/
	black tests/

# 代码检查
lint:
	flake8 k8s_diagnosis_agent/
	mypy k8s_diagnosis_agent/

# 创建环境配置文件
setup-env:
	@if [ ! -f .env ]; then \
		echo "创建 .env 配置文件..."; \
		cp .env.example .env; \
		echo "请编辑 .env 文件配置您的 API 密钥"; \
	else \
		echo ".env 文件已存在"; \
	fi

# 检查环境
check:
	@echo "检查Python版本..."
	@python --version
	@echo "检查pip版本..."
	@pip --version
	@echo "检查kubectl..."
	@kubectl version --client=true || echo "kubectl 未安装"
	@echo "检查Docker..."
	@docker --version || echo "Docker 未安装"

# 完整设置
setup: check setup-env install
	@echo "设置完成！"
	@echo "请编辑 .env 文件配置 API 密钥，然后运行："
	@echo "  make run-web      # 启动Web服务"
	@echo "  make run-interactive  # 启动交互式模式" 