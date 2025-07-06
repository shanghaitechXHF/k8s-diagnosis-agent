# 🔧 K8s Diagnosis Agent

专业的Kubernetes集群故障诊断AI助手，采用先进的AI技术帮助您快速诊断和解决k8s集群问题。

## ✨ 特性

- 🧠 **智能诊断**: 基于大模型的智能planning和执行
- 🔨 **内置工具**: 丰富的k8s和系统诊断工具集
- 🔌 **MCP支持**: 支持Model Context Protocol扩展外部工具
- 🤖 **多模型支持**: 支持GPT-4、Claude 4、DeepSeek V3等主流大模型
- 💬 **多轮对话**: 像Cursor Agent一样的对话体验
- 🌐 **Web界面**: 现代化的Web界面和API接口
- 📱 **多种交互方式**: Web、CLI、交互式多种使用方式

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Kubernetes集群访问权限
- 至少一个大模型API密钥

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/k8s-diagnosis-agent.git
cd k8s-diagnosis-agent

# 安装依赖
pip install -r requirements.txt

# 或使用pip安装
pip install -e .
```

### 配置

1. 复制环境配置文件：
```bash
cp .env.example .env
```

2. 编辑`.env`文件，配置API密钥：
```env
# 选择一个默认模型
DEFAULT_MODEL=gpt-4

# 配置相应的API密钥
OPENAI_API_KEY=your_openai_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Kubernetes配置（可选）
KUBECONFIG_PATH=~/.kube/config
```

### 运行

#### Web服务模式（推荐）
```bash
# 启动Web服务
python -m k8s_diagnosis_agent --mode web

# 或使用uvicorn直接启动
uvicorn k8s_diagnosis_agent.web.app:app --host 0.0.0.0 --port 8000
```

访问: http://localhost:8000

#### 交互式模式
```bash
python -m k8s_diagnosis_agent --mode interactive
```

#### 使用pip安装后
```bash
k8s-diagnosis-agent --mode web
```

## 📖 使用指南

### Web界面使用

1. 打开浏览器访问 http://localhost:8000
2. 在聊天界面描述您的k8s问题
3. Agent会自动分析问题并执行相应的诊断工具
4. 查看诊断结果和解决建议

### API接口

#### 聊天接口
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "我的Pod无法启动，请帮我诊断",
       "stream": false
     }'
```

#### 工具执行接口
```bash
curl -X POST "http://localhost:8000/api/v1/tool" \
     -H "Content-Type: application/json" \
     -d '{
       "tool_name": "k8s_cluster_info",
       "params": {}
     }'
```

#### 获取可用工具
```bash
curl "http://localhost:8000/api/v1/tools"
```

### 命令行使用

```bash
# 交互式聊天
python -m k8s_diagnosis_agent --mode interactive

# 查看帮助
python -m k8s_diagnosis_agent --help
```

## 🛠️ 内置工具

### Kubernetes工具
- `k8s_cluster_info`: 获取集群基本信息
- `k8s_node_info`: 获取节点详细信息
- `k8s_pod_info`: 获取Pod详细信息
- `k8s_service_info`: 获取服务信息
- `k8s_events`: 获取事件信息
- `k8s_logs`: 获取Pod日志
- `k8s_resource_usage`: 获取资源使用情况
- `k8s_network`: 网络诊断
- `k8s_storage`: 存储诊断
- `k8s_security`: 安全诊断

### 系统工具
- `system_info`: 获取系统基本信息
- `network_diagnostic`: 网络连通性诊断
- `filesystem`: 文件系统诊断
- `process`: 进程诊断

## 🔧 配置说明

### 大模型配置

支持多种大模型提供者：

```env
# OpenAI/GPT
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4-turbo

# Claude
CLAUDE_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-opus-20240229

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_MODEL=deepseek-chat
```

### Kubernetes配置

```env
# kubeconfig路径
KUBECONFIG_PATH=~/.kube/config

# 集群配置
CLUSTER_NAME=my-cluster
K8S_NAMESPACE=default

# 集群内配置（Pod内运行时）
USE_IN_CLUSTER_CONFIG=true
```

### Web服务配置

```env
WEB_HOST=0.0.0.0
WEB_PORT=8000
DEBUG=false
CORS_ORIGINS=["*"]
```

## 🌟 示例对话

```
用户: 我的Pod一直处于Pending状态，请帮我诊断

助手: 我来帮您诊断Pod处于Pending状态的问题。让我先收集一些信息。

[执行工具: k8s_cluster_info]
[执行工具: k8s_node_info]
[执行工具: k8s_pod_info]
[执行工具: k8s_events]

根据诊断结果，我发现以下问题：

1. 集群节点资源不足：CPU使用率已达到95%
2. 有3个节点处于NotReady状态
3. 事件显示："Failed to schedule pod: Insufficient cpu"

建议解决方案：
1. 扩容集群节点或删除不必要的Pod释放资源
2. 检查NotReady节点的状态并进行修复
3. 调整Pod的资源请求和限制

需要我帮您执行具体的修复操作吗？
```

## 🔌 MCP支持

支持Model Context Protocol，可以扩展外部工具：

```python
# 注册外部工具
from k8s_diagnosis_agent.tools import tool_registry

# 自定义工具类
class CustomTool(BaseTool):
    async def execute(self, **kwargs):
        # 工具实现
        pass

# 注册工具
tool_registry.register("custom_tool", CustomTool)
```

## 📁 项目结构

```
k8s-diagnosis-agent/
├── k8s_diagnosis_agent/
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── cli.py             # 命令行界面
│   ├── core/              # 核心模块
│   │   ├── agent.py       # 主Agent类
│   │   ├── planner.py     # 计划器
│   │   ├── executor.py    # 执行器
│   │   ├── conversation.py # 对话管理
│   │   └── session.py     # 会话管理
│   ├── llm/               # LLM提供者
│   │   ├── base.py        # 基础抽象类
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   ├── deepseek_provider.py
│   │   └── factory.py     # LLM工厂
│   ├── tools/             # 工具集
│   │   ├── base.py        # 工具基类
│   │   ├── k8s_tools.py   # k8s工具
│   │   ├── system_tools.py # 系统工具
│   │   └── registry.py    # 工具注册表
│   └── web/               # Web服务
│       ├── app.py         # Web应用
│       ├── api.py         # API路由
│       └── models.py      # 数据模型
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## 🤝 贡献

欢迎贡献代码！请查看[贡献指南](CONTRIBUTING.md)。

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🆘 支持

- 📖 [文档](https://github.com/your-username/k8s-diagnosis-agent/wiki)
- 🐛 [问题反馈](https://github.com/your-username/k8s-diagnosis-agent/issues)
- 💬 [讨论区](https://github.com/your-username/k8s-diagnosis-agent/discussions)

## 🙏 致谢

感谢所有贡献者和以下开源项目：

- [Kubernetes](https://kubernetes.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenAI](https://openai.com/)
- [Anthropic](https://anthropic.com/)

---

⭐ 如果这个项目对您有帮助，请给我们一个star！