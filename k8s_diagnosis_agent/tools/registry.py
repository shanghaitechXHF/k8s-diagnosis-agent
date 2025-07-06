"""
工具注册表
"""
from typing import Dict, List, Optional, Type, Any
from .base import BaseTool
from .k8s_tools import (
    KubernetesClusterInfoTool,
    KubernetesNodeInfoTool,
    KubernetesPodInfoTool,
    KubernetesServiceInfoTool,
    KubernetesEventsTool,
    KubernetesLogsTool,
    KubernetesResourceUsageTool,
    KubernetesNetworkTool,
    KubernetesStorageTool,
    KubernetesSecurityTool,
)
from .system_tools import (
    SystemInfoTool,
    NetworkDiagnosticTool,
    FileSystemTool,
    ProcessTool,
)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._tool_instances: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # Kubernetes工具
        self.register("k8s_cluster_info", KubernetesClusterInfoTool)
        self.register("k8s_node_info", KubernetesNodeInfoTool)
        self.register("k8s_pod_info", KubernetesPodInfoTool)
        self.register("k8s_service_info", KubernetesServiceInfoTool)
        self.register("k8s_events", KubernetesEventsTool)
        self.register("k8s_logs", KubernetesLogsTool)
        self.register("k8s_resource_usage", KubernetesResourceUsageTool)
        self.register("k8s_network", KubernetesNetworkTool)
        self.register("k8s_storage", KubernetesStorageTool)
        self.register("k8s_security", KubernetesSecurityTool)
        
        # 系统工具
        self.register("system_info", SystemInfoTool)
        self.register("network_diagnostic", NetworkDiagnosticTool)
        self.register("filesystem", FileSystemTool)
        self.register("process", ProcessTool)
    
    def register(self, name: str, tool_class: Type[BaseTool]):
        """注册工具"""
        self._tools[name] = tool_class
    
    def unregister(self, name: str):
        """取消注册工具"""
        if name in self._tools:
            del self._tools[name]
        if name in self._tool_instances:
            del self._tool_instances[name]
    
    def get_tool(self, name: str, config: Optional[Dict[str, Any]] = None) -> BaseTool:
        """获取工具实例"""
        if name not in self._tools:
            raise ValueError(f"工具 '{name}' 未注册")
        
        # 如果已有实例且配置相同，返回现有实例
        if name in self._tool_instances and not config:
            return self._tool_instances[name]
        
        # 创建新实例
        tool_class = self._tools[name]
        tool_instance = tool_class(config)
        self._tool_instances[name] = tool_instance
        
        return tool_instance
    
    def get_all_tools(self) -> List[str]:
        """获取所有注册的工具名称"""
        return list(self._tools.keys())
    
    def get_k8s_tools(self) -> List[str]:
        """获取k8s相关工具"""
        return [name for name in self._tools.keys() if name.startswith("k8s_")]
    
    def get_system_tools(self) -> List[str]:
        """获取系统相关工具"""
        return [name for name in self._tools.keys() if not name.startswith("k8s_")]
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的schema"""
        schemas = []
        for name in self._tools.keys():
            tool = self.get_tool(name)
            schema = tool.get_schema()
            schemas.append(schema)
        return schemas
    
    def get_tool_info(self, name: str) -> Dict[str, Any]:
        """获取工具信息"""
        if name not in self._tools:
            raise ValueError(f"工具 '{name}' 未注册")
        
        tool = self.get_tool(name)
        return {
            "name": name,
            "description": tool.get_description(),
            "schema": tool.get_schema(),
            "class": tool.__class__.__name__
        }
    
    def list_tools_by_category(self) -> Dict[str, List[str]]:
        """按类别列出工具"""
        return {
            "kubernetes": self.get_k8s_tools(),
            "system": self.get_system_tools()
        }


# 全局工具注册表实例
tool_registry = ToolRegistry() 