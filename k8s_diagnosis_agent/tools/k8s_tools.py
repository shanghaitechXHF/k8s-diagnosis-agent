"""
Kubernetes诊断工具集合
"""
import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from kubernetes import client, config
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException

from .base import BaseTool, ToolResult, ToolStatus


class KubernetesBaseTool(BaseTool):
    """Kubernetes基础工具类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.k8s_client = None
        self.v1: CoreV1Api = None  # type: ignore
        self.apps_v1 = None
        self.networking_v1 = None
        self.metrics_v1beta1 = None
        
    async def _init_k8s_client(self):
        """初始化k8s客户端"""
        try:
            if self.config.get('use_in_cluster_config'):
                config.load_incluster_config()
            else:
                kubeconfig_path = self.config.get('kubeconfig_path')
                if kubeconfig_path:
                    config.load_kube_config(config_file=kubeconfig_path)
                else:
                    config.load_kube_config()
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            
            # 尝试初始化metrics API（可能不可用）
            try:
                from kubernetes import client as k8s_client
                self.metrics_v1beta1 = k8s_client.CustomObjectsApi()
            except ImportError:
                pass
                
        except Exception as e:
            raise Exception(f"无法初始化Kubernetes客户端: {str(e)}")


class KubernetesClusterInfoTool(KubernetesBaseTool):
    """获取集群信息工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Kubernetes集群基本信息"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取集群信息"""
        try:
            await self._init_k8s_client()
            
            # 获取集群版本
            version_info = await asyncio.to_thread(lambda: client.VersionApi().get_code())
            
            # 获取节点信息
            nodes = await asyncio.to_thread(lambda: self.v1.list_node())
            
            # 获取命名空间
            namespaces = await asyncio.to_thread(lambda: self.v1.list_namespace())
            
            cluster_info = {
                "version": {
                    "major": getattr(version_info, 'major', None),
                    "minor": getattr(version_info, 'minor', None),
                    "git_version": getattr(version_info, 'git_version', None),
                    "platform": getattr(version_info, 'platform', None)
                },
                "nodes": {
                    "total": len(nodes.items),
                    "ready": len([n for n in nodes.items if self._is_node_ready(n)]),
                    "master": len([n for n in nodes.items if self._is_master_node(n)]),
                    "worker": len([n for n in nodes.items if not self._is_master_node(n)])
                },
                "namespaces": {
                    "total": len(namespaces.items),
                    "active": len([ns for ns in namespaces.items if ns.status.phase == "Active"]),
                    "names": [ns.metadata.name for ns in namespaces.items]
                }
            }
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=cluster_info,
                message="成功获取集群信息"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取集群信息失败"
            )
    
    def _is_node_ready(self, node) -> bool:
        """检查节点是否就绪"""
        if not node.status.conditions:
            return False
        
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition.status == "True"
        return False
    
    def _is_master_node(self, node) -> bool:
        """检查是否为master节点"""
        labels = node.metadata.labels or {}
        return any(key in labels for key in [
            "node-role.kubernetes.io/master",
            "node-role.kubernetes.io/control-plane"
        ])
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具JSON Schema"""
        return {
            "type": "function",
            "function": {
                "name": "get_cluster_info",
                "description": "获取Kubernetes集群基本信息",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


class KubernetesNodeInfoTool(KubernetesBaseTool):
    """获取节点信息工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Kubernetes节点详细信息"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取节点信息"""
        try:
            await self._init_k8s_client()
            
            node_name = kwargs.get('node_name')
            
            if node_name:
                # 获取特定节点
                node = await asyncio.to_thread(self.v1.read_node, node_name)
                nodes_data = [self._format_node_info(node)]
            else:
                # 获取所有节点
                nodes = await asyncio.to_thread(self.v1.list_node)
                nodes_data = [self._format_node_info(node) for node in nodes.items]
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"nodes": nodes_data},
                message=f"成功获取节点信息"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取节点信息失败"
            )
    
    def _format_node_info(self, node) -> Dict[str, Any]:
        """格式化节点信息"""
        conditions = {}
        if node.status.conditions:
            for condition in node.status.conditions:
                conditions[condition.type] = {
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message
                }
        
        return {
            "name": node.metadata.name,
            "labels": node.metadata.labels or {},
            "annotations": node.metadata.annotations or {},
            "status": {
                "conditions": conditions,
                "node_info": {
                    "os_image": node.status.node_info.os_image,
                    "kernel_version": node.status.node_info.kernel_version,
                    "container_runtime_version": node.status.node_info.container_runtime_version,
                    "kubelet_version": node.status.node_info.kubelet_version,
                    "kube_proxy_version": node.status.node_info.kube_proxy_version,
                },
                "capacity": node.status.capacity,
                "allocatable": node.status.allocatable,
                "addresses": [{"type": addr.type, "address": addr.address} 
                             for addr in (node.status.addresses or [])]
            }
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具JSON Schema"""
        return {
            "type": "function",
            "function": {
                "name": "get_node_info",
                "description": "获取Kubernetes节点详细信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "node_name": {
                            "type": "string",
                            "description": "节点名称，如果不提供则获取所有节点"
                        }
                    },
                    "required": []
                }
            }
        }


class KubernetesPodInfoTool(KubernetesBaseTool):
    """获取Pod信息工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Pod详细信息"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取Pod信息"""
        try:
            await self._init_k8s_client()
            
            namespace = kwargs.get('namespace', 'default')
            pod_name = kwargs.get('pod_name')
            label_selector = kwargs.get('label_selector')
            
            if pod_name:
                # 获取特定Pod
                pod = await asyncio.to_thread(self.v1.read_namespaced_pod, pod_name, namespace)
                pods_data = [self._format_pod_info(pod)]
            else:
                # 获取多个Pod
                pods = await asyncio.to_thread(
                    self.v1.list_namespaced_pod,
                    namespace,
                    label_selector=label_selector
                )
                pods_data = [self._format_pod_info(pod) for pod in pods.items]
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"pods": pods_data},
                message=f"成功获取Pod信息"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取Pod信息失败"
            )
    
    def _format_pod_info(self, pod) -> Dict[str, Any]:
        """格式化Pod信息"""
        containers = []
        if pod.spec.containers:
            for container in pod.spec.containers:
                containers.append({
                    "name": container.name,
                    "image": container.image,
                    "resources": {
                        "requests": container.resources.requests or {} if container.resources else {},
                        "limits": container.resources.limits or {} if container.resources else {}
                    },
                    "ports": [{"containerPort": port.container_port, "protocol": port.protocol} 
                             for port in (container.ports or [])]
                })
        
        conditions = {}
        if pod.status.conditions:
            for condition in pod.status.conditions:
                conditions[condition.type] = {
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message
                }
        
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "labels": pod.metadata.labels or {},
            "annotations": pod.metadata.annotations or {},
            "node_name": pod.spec.node_name,
            "phase": pod.status.phase,
            "conditions": conditions,
            "containers": containers,
            "restart_policy": pod.spec.restart_policy,
            "creation_timestamp": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具JSON Schema"""
        return {
            "type": "function",
            "function": {
                "name": "get_pod_info",
                "description": "获取Pod详细信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "命名空间",
                            "default": "default"
                        },
                        "pod_name": {
                            "type": "string",
                            "description": "Pod名称，如果不提供则获取命名空间下所有Pod"
                        },
                        "label_selector": {
                            "type": "string",
                            "description": "标签选择器，用于过滤Pod"
                        }
                    },
                    "required": []
                }
            }
        }


class KubernetesEventsTool(KubernetesBaseTool):
    """获取事件信息工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Kubernetes事件信息"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取事件信息"""
        try:
            await self._init_k8s_client()
            
            namespace = kwargs.get('namespace', 'default')
            field_selector = kwargs.get('field_selector')
            
            events = await asyncio.to_thread(
                self.v1.list_namespaced_event,
                namespace,
                field_selector=field_selector
            )
            
            events_data = []
            for event in events.items:
                events_data.append({
                    "name": event.metadata.name,
                    "namespace": event.metadata.namespace,
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "count": event.count,
                    "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
                    "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
                    "involved_object": {
                        "kind": event.involved_object.kind,
                        "name": event.involved_object.name,
                        "namespace": event.involved_object.namespace
                    }
                })
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"events": events_data},
                message=f"成功获取事件信息"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取事件信息失败"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具JSON Schema"""
        return {
            "type": "function",
            "function": {
                "name": "get_k8s_events",
                "description": "获取Kubernetes事件信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "命名空间",
                            "default": "default"
                        },
                        "field_selector": {
                            "type": "string",
                            "description": "字段选择器，用于过滤事件"
                        }
                    },
                    "required": []
                }
            }
        }


class KubernetesLogsTool(KubernetesBaseTool):
    """获取Pod日志工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Pod日志"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取Pod日志"""
        try:
            await self._init_k8s_client()
            
            namespace = kwargs.get('namespace', 'default')
            pod_name = kwargs.get('pod_name')
            container_name = kwargs.get('container_name')
            tail_lines = kwargs.get('tail_lines', 100)
            since_seconds = kwargs.get('since_seconds')
            
            if not pod_name:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="pod_name是必需的参数",
                    message="获取日志失败"
                )
            
            logs = await asyncio.to_thread(
                self.v1.read_namespaced_pod_log,
                pod_name,
                namespace,
                container=container_name,
                tail_lines=tail_lines,
                since_seconds=since_seconds
            )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "container": container_name,
                    "logs": logs
                },
                message=f"成功获取Pod日志"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取Pod日志失败"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具JSON Schema"""
        return {
            "type": "function",
            "function": {
                "name": "get_pod_logs",
                "description": "获取Pod日志",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "命名空间",
                            "default": "default"
                        },
                        "pod_name": {
                            "type": "string",
                            "description": "Pod名称"
                        },
                        "container_name": {
                            "type": "string",
                            "description": "容器名称（如果Pod有多个容器）"
                        },
                        "tail_lines": {
                            "type": "integer",
                            "description": "获取最后N行日志",
                            "default": 100
                        },
                        "since_seconds": {
                            "type": "integer",
                            "description": "获取最近N秒的日志"
                        }
                    },
                    "required": ["pod_name"]
                }
            }
        }


# 简化版本的其他工具类
class KubernetesServiceInfoTool(KubernetesBaseTool):
    """获取服务信息工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Kubernetes服务信息"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取服务信息"""
        try:
            await self._init_k8s_client()
            
            namespace = kwargs.get('namespace', 'default')
            service_name = kwargs.get('service_name')
            
            if service_name:
                service = await asyncio.to_thread(self.v1.read_namespaced_service, service_name, namespace)
                services_data = [self._format_service_info(service)]
            else:
                services = await asyncio.to_thread(self.v1.list_namespaced_service, namespace)
                services_data = [self._format_service_info(svc) for svc in services.items]
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"services": services_data},
                message="成功获取服务信息"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取服务信息失败"
            )
    
    def _format_service_info(self, service) -> Dict[str, Any]:
        """格式化服务信息"""
        return {
            "name": service.metadata.name,
            "namespace": service.metadata.namespace,
            "type": service.spec.type,
            "cluster_ip": service.spec.cluster_ip,
            "external_ips": service.spec.external_i_ps or [],
            "ports": [{"port": port.port, "target_port": port.target_port, "protocol": port.protocol} 
                     for port in (service.spec.ports or [])],
            "selector": service.spec.selector or {}
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_service_info",
                "description": "获取Kubernetes服务信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string", "default": "default"},
                        "service_name": {"type": "string"}
                    },
                    "required": []
                }
            }
        }


class KubernetesResourceUsageTool(KubernetesBaseTool):
    """获取资源使用情况工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取Kubernetes资源使用情况"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取资源使用情况"""
        return ToolResult(
            status=ToolStatus.INFO,
            message="资源使用情况获取功能需要metrics-server支持",
            data={}
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_resource_usage",
                "description": "获取Kubernetes资源使用情况",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }


class KubernetesNetworkTool(KubernetesBaseTool):
    """网络诊断工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "Kubernetes网络诊断"
    
    async def execute(self, **kwargs) -> ToolResult:
        """网络诊断"""
        return ToolResult(
            status=ToolStatus.INFO,
            message="网络诊断功能待实现",
            data={}
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "diagnose_network",
                "description": "Kubernetes网络诊断",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }


class KubernetesStorageTool(KubernetesBaseTool):
    """存储诊断工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "Kubernetes存储诊断"
    
    async def execute(self, **kwargs) -> ToolResult:
        """存储诊断"""
        return ToolResult(
            status=ToolStatus.INFO,
            message="存储诊断功能待实现",
            data={}
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "diagnose_storage",
                "description": "Kubernetes存储诊断",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }


class KubernetesSecurityTool(KubernetesBaseTool):
    """安全诊断工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "Kubernetes安全诊断"
    
    async def execute(self, **kwargs) -> ToolResult:
        """安全诊断"""
        return ToolResult(
            status=ToolStatus.INFO,
            message="安全诊断功能待实现",
            data={}
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "diagnose_security",
                "description": "Kubernetes安全诊断",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        } 