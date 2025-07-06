# K8s Diagnosis Agent Helm Chart

这是一个用于部署K8s故障诊断AI Agent的Helm Chart。

## 安装

### 前提条件

- Kubernetes 1.16+
- Helm 3.0+

### 安装Chart

```bash
# 添加仓库
helm repo add k8s-diagnosis-agent https://your-helm-repo.com/charts

# 更新仓库
helm repo update

# 安装
helm install my-k8s-diagnosis-agent k8s-diagnosis-agent/k8s-diagnosis-agent

# 或者从本地安装
helm install my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent
```

### 配置LLM API密钥

```bash
# 创建包含API密钥的values文件
cat > values-secret.yaml << EOF
secrets:
  llmApiKeys:
    openai: "your-openai-api-key"
    claude: "your-claude-api-key"
    deepseek: "your-deepseek-api-key"
EOF

# 使用自定义values安装
helm install my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f values-secret.yaml
```

### 启用Ingress

```bash
cat > values-ingress.yaml << EOF
ingress:
  enabled: true
  className: nginx
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: k8s-diagnosis.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: k8s-diagnosis-tls
      hosts:
        - k8s-diagnosis.yourdomain.com
EOF

helm upgrade my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f values-ingress.yaml
```

### 多集群支持

```bash
cat > values-multicluster.yaml << EOF
multiCluster:
  enabled: true
  clusters:
    - name: cluster1
      kubeconfig: |
        apiVersion: v1
        kind: Config
        # cluster1的kubeconfig内容
    - name: cluster2
      kubeconfig: |
        apiVersion: v1
        kind: Config
        # cluster2的kubeconfig内容

configMap:
  kubeconfig:
    enabled: true
EOF

helm upgrade my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f values-multicluster.yaml
```

### SSH支持

```bash
# 生成SSH密钥对
ssh-keygen -t rsa -b 4096 -f ./id_rsa -N ""

# 创建SSH配置
cat > values-ssh.yaml << EOF
secrets:
  ssh:
    enabled: true
    privateKey: |
$(cat id_rsa | sed 's/^/      /')
    knownHosts: |
      # 在这里添加known_hosts内容
EOF

helm upgrade my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f values-ssh.yaml
```

### 权限配置

```bash
cat > values-permissions.yaml << EOF
config:
  permissions:
    enabled: true
    defaultRole: "viewer"
    roles:
      admin:
        description: "管理员权限"
        tools: ["*"]
        commands: ["*"]
        kubeconfig: true
        ssh: true
      operator:
        description: "运维人员权限"
        tools: ["k8s_*", "system_*"]
        commands: ["get", "describe", "logs"]
        kubeconfig: true
        ssh: true
      viewer:
        description: "只读权限"
        tools: ["k8s_cluster_info", "k8s_node_info", "k8s_pod_info"]
        commands: ["get", "describe"]
        kubeconfig: false
        ssh: false
EOF

helm upgrade my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f values-permissions.yaml
```

## 卸载

```bash
helm uninstall my-k8s-diagnosis-agent
```

## 配置参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `replicaCount` | 副本数 | `1` |
| `image.repository` | 镜像仓库 | `k8s-diagnosis-agent` |
| `image.tag` | 镜像标签 | `0.1.0` |
| `image.pullPolicy` | 镜像拉取策略 | `IfNotPresent` |
| `service.type` | 服务类型 | `ClusterIP` |
| `service.port` | 服务端口 | `8000` |
| `ingress.enabled` | 启用Ingress | `false` |
| `resources.limits.cpu` | CPU限制 | `1000m` |
| `resources.limits.memory` | 内存限制 | `1Gi` |
| `resources.requests.cpu` | CPU请求 | `500m` |
| `resources.requests.memory` | 内存请求 | `512Mi` |
| `autoscaling.enabled` | 启用自动扩缩容 | `false` |
| `config.permissions.enabled` | 启用权限管理 | `true` |
| `secrets.llmApiKeys.openai` | OpenAI API密钥 | `""` |
| `secrets.llmApiKeys.claude` | Claude API密钥 | `""` |
| `secrets.llmApiKeys.deepseek` | DeepSeek API密钥 | `""` |
| `secrets.ssh.enabled` | 启用SSH支持 | `false` |
| `multiCluster.enabled` | 启用多集群支持 | `false` |
| `persistence.enabled` | 启用持久化存储 | `false` |
| `rbac.create` | 创建RBAC资源 | `true` |
| `monitoring.enabled` | 启用监控 | `false` |

## 故障排除

### 1. Pod启动失败

```bash
# 检查Pod状态
kubectl get pods -l app.kubernetes.io/name=k8s-diagnosis-agent

# 查看Pod日志
kubectl logs -l app.kubernetes.io/name=k8s-diagnosis-agent

# 检查Pod详情
kubectl describe pod <pod-name>
```

### 2. 无法访问服务

```bash
# 检查Service状态
kubectl get svc -l app.kubernetes.io/name=k8s-diagnosis-agent

# 检查Ingress状态
kubectl get ingress -l app.kubernetes.io/name=k8s-diagnosis-agent

# 端口转发测试
kubectl port-forward svc/my-k8s-diagnosis-agent 8000:8000
```

### 3. 权限问题

```bash
# 检查ServiceAccount
kubectl get sa -l app.kubernetes.io/name=k8s-diagnosis-agent

# 检查ClusterRole和ClusterRoleBinding
kubectl get clusterrole -l app.kubernetes.io/name=k8s-diagnosis-agent
kubectl get clusterrolebinding -l app.kubernetes.io/name=k8s-diagnosis-agent
```

### 4. 配置问题

```bash
# 检查ConfigMap
kubectl get configmap -l app.kubernetes.io/name=k8s-diagnosis-agent

# 检查Secret
kubectl get secret -l app.kubernetes.io/name=k8s-diagnosis-agent

# 查看配置内容
kubectl describe configmap <configmap-name>
```

## 升级

```bash
# 升级到新版本
helm upgrade my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent

# 回滚到上一版本
helm rollback my-k8s-diagnosis-agent 1
```

## 备份和恢复

```bash
# 备份Helm发布
helm get values my-k8s-diagnosis-agent > backup-values.yaml

# 恢复
helm install my-k8s-diagnosis-agent ./helm/k8s-diagnosis-agent -f backup-values.yaml
``` 