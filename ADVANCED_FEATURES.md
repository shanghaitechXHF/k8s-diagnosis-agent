# K8s诊断Agent高级功能实现

本文档描述了在基础版本基础上新增的五个高级功能的实现。

## 功能概览

✅ **已完成的高级功能**：

1. **Helm Chart部署支持** - 支持在k8s集群中使用Helm部署
2. **多Python版本支持** - 支持Python 3.9、3.10、3.11、3.12的环境管理
3. **SSH节点访问** - 支持通过SSH登录到k8s集群节点进行诊断
4. **权限管理系统** - 对不同权限用户提供不同范围的工具和命令
5. **动态Kubeconfig** - 支持用户动态提供不同的Kubeconfig进行集群诊断

## 1. Helm Chart部署支持

### 功能特性
- 完整的Helm Chart模板支持
- 多架构镜像构建（linux/amd64, linux/arm64）
- 配置管理和密钥管理
- RBAC权限配置
- 持久化存储支持
- 自动扩缩容（HPA）
- 监控集成（ServiceMonitor）

### 主要文件
```
helm/k8s-diagnosis-agent/
├── Chart.yaml                 # Chart基础信息
├── values.yaml               # 默认配置值
├── templates/
│   ├── deployment.yaml       # 部署模板
│   ├── service.yaml          # 服务模板
│   ├── configmap.yaml        # 配置映射
│   ├── secret.yaml           # 密钥模板
│   ├── rbac.yaml             # RBAC配置
│   ├── serviceaccount.yaml   # 服务账户
│   ├── ingress.yaml          # Ingress配置
│   ├── pvc.yaml              # 持久化卷
│   ├── hpa.yaml              # 水平扩容
│   ├── servicemonitor.yaml   # 监控配置
│   └── _helpers.tpl          # 辅助模板
└── README.md                 # 部署说明
```

### 使用方式
```bash
# 安装Chart
helm install my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent

# 使用自定义配置
helm install my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f custom-values.yaml

# 升级
helm upgrade my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent
```

## 2. 多Python版本支持

### 功能特性
- 支持Python 3.9、3.10、3.11、3.12四个版本
- 版本特定的依赖管理
- 多版本Docker镜像构建
- Tox多环境测试
- 自动化构建脚本

### 主要文件
```
requirements/
├── python39.txt              # Python 3.9依赖
├── python310.txt             # Python 3.10依赖
├── python311.txt             # Python 3.11依赖
├── python312.txt             # Python 3.12依赖
└── test.txt                  # 测试依赖

scripts/
└── build-multi-version.sh    # 多版本构建脚本

tox.ini                       # 多环境测试配置
Dockerfile.python39           # Python 3.9镜像
```

### 使用方式
```bash
# 构建所有版本镜像
./scripts/build-multi-version.sh

# 构建特定版本
./scripts/build-multi-version.sh --python-versions "3.9 3.11"

# 运行多环境测试
tox

# 运行特定环境测试
tox -e py39
```

## 3. SSH节点访问功能

### 功能特性
- 异步SSH连接管理
- SSH会话池和生命周期管理
- 远程命令执行
- 文件传输（上传/下载）
- 系统信息收集
- K8s节点诊断工具
- 日志获取工具

### 主要文件
```
k8s_diagnosis_agent/ssh/
├── __init__.py              # 模块初始化
├── client.py                # SSH客户端实现
├── manager.py               # SSH连接管理器
└── tools.py                 # SSH工具集合
```

### 核心组件

#### SSH客户端 (`SSHClient`)
- 支持密码和密钥认证
- 异步命令执行
- 文件传输功能
- 连接状态监控

#### SSH管理器 (`SSHManager`)
- 连接池管理
- 会话生命周期
- 重连机制
- 配置持久化

#### SSH工具集
- `SSHRemoteSystemInfoTool` - 获取远程系统信息
- `SSHRemoteCommandTool` - 执行远程命令
- `SSHRemoteK8sInfoTool` - K8s节点信息获取
- `SSHRemoteLogTool` - 远程日志获取
- `SSHSessionManagerTool` - 会话管理

### 使用示例
```python
# 创建SSH会话
await ssh_manager.create_session(SSHConnectionInfo(
    host="192.168.1.100",
    username="ubuntu",
    password="password"
))

# 执行远程命令
result = await ssh_tools.execute_tool("ssh_remote_command", 
    command="kubectl get pods",
    session_id="ssh_session_1"
)
```

## 4. 权限管理系统

### 功能特性
- 基于角色的访问控制（RBAC）
- 用户认证和会话管理
- 工具和命令级别的权限控制
- 预定义角色（admin、operator、viewer）
- 权限装饰器和中间件
- 账户锁定和安全策略

### 主要文件
```
k8s_diagnosis_agent/auth/
├── __init__.py              # 模块初始化
├── models.py                # 数据模型（User、Role、Permission）
├── manager.py               # 权限管理器
├── decorators.py            # 权限装饰器
└── middleware.py            # FastAPI中间件
```

### 核心组件

#### 数据模型
- `User` - 用户模型，包含角色、会话管理
- `Role` - 角色模型，定义权限集合
- `Permission` - 权限模型，定义具体权限
- `PermissionType` - 权限类型枚举

#### 权限管理器 (`AuthManager`)
- 用户认证和会话管理
- 权限检查和验证
- 用户和角色管理
- 配置持久化

#### 预定义角色
- **admin** - 管理员权限，可访问所有功能
- **operator** - 运维人员权限，可执行诊断工具和K8s命令
- **viewer** - 只读权限，仅可查看信息

### 使用示例
```python
# 用户认证
success, token, error = await auth_manager.authenticate("admin", "password")

# 权限检查
can_ssh = await auth_manager.check_ssh_permission(token)
can_tool = await auth_manager.check_tool_permission(token, "k8s_cluster_info")

# 装饰器使用
@require_tool_permission(auth_manager, "k8s_node_info")
async def get_node_info(**kwargs):
    pass
```

## 5. 动态Kubeconfig支持

### 功能特性
- 多集群配置管理
- 动态配置切换
- Kubeconfig验证和解析
- 临时文件管理
- 配置持久化
- 集群信息提取

### 主要文件
```
k8s_diagnosis_agent/kubeconfig/
├── __init__.py              # 模块初始化
├── models.py                # Kubeconfig数据模型
├── manager.py               # Kubeconfig管理器
└── provider.py              # 配置提供者
```

### 核心组件

#### 数据模型
- `KubeconfigInfo` - Kubeconfig完整信息
- `ClusterInfo` - 集群信息
- `UserInfo` - 用户认证信息
- `ContextInfo` - 上下文信息

#### 主要功能
- YAML格式转换
- 配置验证
- 临时文件创建
- 多格式支持（字典、文件、字符串）

### 使用示例
```python
# 从文件加载Kubeconfig
kubeconfig = KubeconfigInfo.from_yaml_file(
    "/path/to/kubeconfig", 
    "cluster-1", 
    "生产集群"
)

# 验证配置
errors = kubeconfig.validate()

# 创建临时文件
temp_file = kubeconfig.create_temp_file()

# 获取当前集群信息
cluster_info = kubeconfig.get_current_cluster_info()
```

## 部署和使用

### 1. 使用Helm部署到K8s集群

```bash
# 克隆项目
git clone <repository>
cd k8s-diagnosis-agent

# 配置values.yaml
cp helm/k8s-diagnosis-agent/values.yaml custom-values.yaml
# 编辑custom-values.yaml，设置API密钥等配置

# 部署到集群
helm install k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f custom-values.yaml

# 检查部署状态
kubectl get pods -l app.kubernetes.io/name=k8s-diagnosis-agent
```

### 2. 多版本开发环境

```bash
# 安装tox
pip install tox

# 运行所有版本测试
tox

# 构建多版本镜像
chmod +x scripts/build-multi-version.sh
./scripts/build-multi-version.sh
```

### 3. 权限配置

```bash
# 启动服务时启用权限管理
python -m k8s_diagnosis_agent --mode web --enable-auth

# 默认管理员账户
用户名: admin
密码: admin123
```

### 4. 使用示例

```python
from k8s_diagnosis_agent import DiagnosisAgent
from k8s_diagnosis_agent.auth import AuthManager
from k8s_diagnosis_agent.ssh import SSHManager
from k8s_diagnosis_agent.kubeconfig import KubeconfigManager

# 创建Agent实例
agent = DiagnosisAgent()

# 权限验证
success, token, _ = await agent.auth_manager.authenticate("admin", "admin123")

# SSH节点访问
ssh_session = await agent.ssh_manager.create_session({
    "host": "k8s-node-1",
    "username": "ubuntu",
    "private_key_path": "/path/to/key"
})

# 使用不同的Kubeconfig
kubeconfig = await agent.kubeconfig_manager.load_from_file("/path/to/kubeconfig")
result = await agent.execute_with_kubeconfig(kubeconfig, "k8s_cluster_info")
```

## 安全考虑

### 1. 权限管理
- 最小权限原则
- 会话超时机制
- 账户锁定策略
- 安全的密码存储

### 2. SSH安全
- 密钥认证优于密码认证
- 连接超时设置
- 会话生命周期管理
- 安全的密钥存储

### 3. Kubeconfig安全
- 临时文件自动清理
- 敏感信息不记录日志
- 配置验证和审计

## 监控和日志

### 1. 系统监控
- Prometheus指标暴露
- 健康检查端点
- 会话状态监控
- 权限审计日志

### 2. 日志记录
- 结构化日志输出
- 用户操作审计
- 错误追踪
- 性能监控

## 扩展性

### 1. 工具扩展
- 插件化工具架构
- 自定义工具开发
- 工具权限绑定

### 2. 认证扩展
- LDAP/AD集成
- OAuth2支持
- 多因素认证

### 3. 存储扩展
- 数据库后端支持
- 配置备份和恢复
- 分布式部署支持

---

通过这些高级功能，K8s诊断Agent现在具备了企业级的部署、安全和管理能力，可以满足不同规模和安全要求的K8s集群故障诊断需求。 