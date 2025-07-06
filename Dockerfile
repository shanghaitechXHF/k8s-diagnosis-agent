FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY k8s_diagnosis_agent/ ./k8s_diagnosis_agent/
COPY README.md ./

# 安装项目
RUN pip install -e .

# 创建非root用户
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["python", "-m", "k8s_diagnosis_agent", "--mode", "web", "--host", "0.0.0.0", "--port", "8000"] 