# K8s Diagnosis Agent 部署指南

本指南介绍如何在不同平台（Linux/Windows/Mac）、Kubernetes集群以及通过Helm Chart部署K8s Diagnosis Agent。

---

## 一、本地二进制部署（Linux/Windows/Mac）

### 1. 依赖环境
- Python 3.9/3.10/3.11/3.12
- pip
- 推荐使用虚拟环境（venv/conda）

### 2. 获取代码
```bash
git clone https://github.com/your-org/k8s-diagnosis-agent.git
cd k8s-diagnosis-agent
```

### 3. 安装依赖

#### 方式一：自动安装
```bash
pip install -r requirements.txt
```

#### 方式二：指定Python版本依赖
```bash
# 以Python 3.9为例
pip install -r requirements/python39.txt
# 其他版本见 requirements/ 目录
```

### 4. 运行Agent
```bash
# 启动Web服务
python -m k8s_diagnosis_agent.web.app

# 启动CLI模式
python -m k8s_diagnosis_agent.cli
```

### 5. Windows/Mac注意事项
- Windows建议使用PowerShell或WSL环境
- Mac需确保已安装Xcode命令行工具

---

## 二、Kubernetes集群直接部署

### 1. 构建镜像
```bash
# 推荐使用多版本构建脚本
bash scripts/build-multi-version.sh
# 或手动构建
# docker build -t your-repo/k8s-diagnosis-agent:latest .
```

### 2. 推送镜像
```bash
docker push your-repo/k8s-diagnosis-agent:latest
```

### 3. 创建K8s资源
```bash
kubectl apply -f k8s-manifest.yaml
# 或根据实际需求自定义Deployment/Service/ConfigMap等
```

### 4. 访问服务
- 通过NodePort/LoadBalancer/Ingress暴露服务
- 参考 `k8s-manifest.yaml` 或 Helm Chart 的 service/ingress 配置

---

## 三、Helm Chart部署

### 1. 进入Helm目录
```bash
cd helm/k8s-diagnosis-agent
```

### 2. 配置values.yaml
- 编辑 `values.yaml`，根据实际环境修改镜像、端口、环境变量等参数

### 3. 安装/升级
```bash
# 安装
helm install diagnosis-agent . -n diagnosis --create-namespace
# 升级
helm upgrade diagnosis-agent . -n diagnosis
```

### 4. 卸载
```bash
helm uninstall diagnosis-agent -n diagnosis
```

### 5. 高级配置
- 支持HPA、PVC、RBAC、ServiceMonitor等高级功能
- 详见 `helm/k8s-diagnosis-agent/README.md`

---

## 四、常见问题

### 1. 如何切换Python版本？
- 使用对应的 requirements/pythonXXX.txt 安装依赖
- 或使用tox进行多版本测试

### 2. 如何自定义配置？
- 支持通过环境变量、ConfigMap、values.yaml等多种方式配置

### 3. 如何集成外部工具（如SSH/MCP）？
- 参考 `MCP_INTEGRATION_GUIDE.md` 文档

### 4. 日志与监控
- 默认输出到标准输出
- 可集成Prometheus、Grafana等监控系统

---

如有更多问题，请查阅项目README或提交Issue。 