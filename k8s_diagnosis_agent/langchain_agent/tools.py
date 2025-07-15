"""
LangChain 工具包装器
将现有的 K8s 诊断工具适配到 LangChain 框架
"""
import json
import asyncio
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# 注意：这些导入在实际环境中需要安装相应的包
# 这里使用 try-except 来处理可能的导入错误
try:
    from langchain.tools import BaseTool
    from langchain.callbacks.manager import CallbackManagerForToolRun
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # 如果 LangChain 不可用，创建模拟类
    class BaseTool:
        def __init__(self):
            self.name = ""
            self.description = ""
            self.args_schema = None
        
        def _run(self, *args, **kwargs):
            raise NotImplementedError("LangChain not available")
        
        async def _arun(self, *args, **kwargs):
            raise NotImplementedError("LangChain not available")
    
    class CallbackManagerForToolRun:
        pass
    
    LANGCHAIN_AVAILABLE = False

from ..config import Config
from ..tools.registry import ToolRegistry
from ..tools.base import ToolResult


class K8sClusterInfoInput(BaseModel):
    """获取集群信息的输入参数"""
    namespace: Optional[str] = Field(default="default", description="命名空间")


class K8sPodInfoInput(BaseModel):
    """获取Pod信息的输入参数"""
    namespace: Optional[str] = Field(default="default", description="命名空间")
    pod_name: Optional[str] = Field(default=None, description="Pod名称")
    label_selector: Optional[str] = Field(default=None, description="标签选择器")


class K8sNodeInfoInput(BaseModel):
    """获取节点信息的输入参数"""
    node_name: Optional[str] = Field(default=None, description="节点名称")


class K8sEventsInput(BaseModel):
    """获取事件信息的输入参数"""
    namespace: Optional[str] = Field(default="default", description="命名空间")
    field_selector: Optional[str] = Field(default=None, description="字段选择器")


class K8sLogsInput(BaseModel):
    """获取日志信息的输入参数"""
    namespace: Optional[str] = Field(default="default", description="命名空间")
    pod_name: str = Field(description="Pod名称")
    container_name: Optional[str] = Field(default=None, description="容器名称")
    tail_lines: Optional[int] = Field(default=100, description="日志行数")


class SystemInfoInput(BaseModel):
    """获取系统信息的输入参数"""
    pass


class K8sToolWrapper:
    """K8s 工具包装器基类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.tool_registry = ToolRegistry()
    
    def _execute_k8s_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 K8s 工具"""
        try:
            tool = self.tool_registry.get_tool(tool_name, self.config.kubernetes.__dict__)
            result = asyncio.run(tool.execute(**params))
            return {
                "status": result.status.value,
                "data": result.data,
                "message": result.message,
                "error": result.error
            }
        except Exception as e:
            return {
                "status": "error",
                "data": None,
                "message": f"执行工具失败: {str(e)}",
                "error": str(e)
            }
    
    async def _execute_k8s_tool_async(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行 K8s 工具"""
        try:
            tool = self.tool_registry.get_tool(tool_name, self.config.kubernetes.__dict__)
            result = await tool.execute(**params)
            return {
                "status": result.status.value,
                "data": result.data,
                "message": result.message,
                "error": result.error
            }
        except Exception as e:
            return {
                "status": "error",
                "data": None,
                "message": f"执行工具失败: {str(e)}",
                "error": str(e)
            }


class K8sClusterInfoTool(BaseTool, K8sToolWrapper):
    """K8s 集群信息工具"""
    
    name = "k8s_cluster_info"
    description = "获取Kubernetes集群的基本信息，包括版本、节点状态、命名空间等"
    args_schema = K8sClusterInfoInput
    
    def __init__(self, config: Config):
        BaseTool.__init__(self)
        K8sToolWrapper.__init__(self, config)
    
    def _run(
        self, 
        namespace: str = "default",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """同步执行"""
        result = self._execute_k8s_tool("k8s_cluster_info", {"namespace": namespace})
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(
        self, 
        namespace: str = "default",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """异步执行"""
        result = await self._execute_k8s_tool_async("k8s_cluster_info", {"namespace": namespace})
        return json.dumps(result, ensure_ascii=False, indent=2)


class K8sPodInfoTool(BaseTool, K8sToolWrapper):
    """K8s Pod 信息工具"""
    
    name = "k8s_pod_info"
    description = "获取Kubernetes Pod的详细信息，包括状态、容器、资源使用等"
    args_schema = K8sPodInfoInput
    
    def __init__(self, config: Config):
        BaseTool.__init__(self)
        K8sToolWrapper.__init__(self, config)
    
    def _run(
        self, 
        namespace: str = "default",
        pod_name: Optional[str] = None,
        label_selector: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """同步执行"""
        params = {"namespace": namespace}
        if pod_name:
            params["pod_name"] = pod_name
        if label_selector:
            params["label_selector"] = label_selector
        
        result = self._execute_k8s_tool("k8s_pod_info", params)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(
        self, 
        namespace: str = "default",
        pod_name: Optional[str] = None,
        label_selector: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """异步执行"""
        params = {"namespace": namespace}
        if pod_name:
            params["pod_name"] = pod_name
        if label_selector:
            params["label_selector"] = label_selector
        
        result = await self._execute_k8s_tool_async("k8s_pod_info", params)
        return json.dumps(result, ensure_ascii=False, indent=2)


class K8sNodeInfoTool(BaseTool, K8sToolWrapper):
    """K8s 节点信息工具"""
    
    name = "k8s_node_info"
    description = "获取Kubernetes节点的详细信息，包括资源、状态、标签等"
    args_schema = K8sNodeInfoInput
    
    def __init__(self, config: Config):
        BaseTool.__init__(self)
        K8sToolWrapper.__init__(self, config)
    
    def _run(
        self, 
        node_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """同步执行"""
        params = {}
        if node_name:
            params["node_name"] = node_name
        
        result = self._execute_k8s_tool("k8s_node_info", params)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(
        self, 
        node_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """异步执行"""
        params = {}
        if node_name:
            params["node_name"] = node_name
        
        result = await self._execute_k8s_tool_async("k8s_node_info", params)
        return json.dumps(result, ensure_ascii=False, indent=2)


class K8sEventsTool(BaseTool, K8sToolWrapper):
    """K8s 事件信息工具"""
    
    name = "k8s_events"
    description = "获取Kubernetes集群事件信息，用于诊断问题"
    args_schema = K8sEventsInput
    
    def __init__(self, config: Config):
        BaseTool.__init__(self)
        K8sToolWrapper.__init__(self, config)
    
    def _run(
        self, 
        namespace: str = "default",
        field_selector: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """同步执行"""
        params = {"namespace": namespace}
        if field_selector:
            params["field_selector"] = field_selector
        
        result = self._execute_k8s_tool("k8s_events", params)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(
        self, 
        namespace: str = "default",
        field_selector: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """异步执行"""
        params = {"namespace": namespace}
        if field_selector:
            params["field_selector"] = field_selector
        
        result = await self._execute_k8s_tool_async("k8s_events", params)
        return json.dumps(result, ensure_ascii=False, indent=2)


class K8sLogsTool(BaseTool, K8sToolWrapper):
    """K8s 日志工具"""
    
    name = "k8s_logs"
    description = "获取Kubernetes Pod的日志信息"
    args_schema = K8sLogsInput
    
    def __init__(self, config: Config):
        BaseTool.__init__(self)
        K8sToolWrapper.__init__(self, config)
    
    def _run(
        self, 
        namespace: str = "default",
        pod_name: str = "",
        container_name: Optional[str] = None,
        tail_lines: int = 100,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """同步执行"""
        params = {
            "namespace": namespace,
            "pod_name": pod_name,
            "tail_lines": tail_lines
        }
        if container_name:
            params["container_name"] = container_name
        
        result = self._execute_k8s_tool("k8s_logs", params)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(
        self, 
        namespace: str = "default",
        pod_name: str = "",
        container_name: Optional[str] = None,
        tail_lines: int = 100,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """异步执行"""
        params = {
            "namespace": namespace,
            "pod_name": pod_name,
            "tail_lines": tail_lines
        }
        if container_name:
            params["container_name"] = container_name
        
        result = await self._execute_k8s_tool_async("k8s_logs", params)
        return json.dumps(result, ensure_ascii=False, indent=2)


class SystemInfoTool(BaseTool, K8sToolWrapper):
    """系统信息工具"""
    
    name = "system_info"
    description = "获取系统基本信息，包括CPU、内存、磁盘等"
    args_schema = SystemInfoInput
    
    def __init__(self, config: Config):
        BaseTool.__init__(self)
        K8sToolWrapper.__init__(self, config)
    
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """同步执行"""
        result = self._execute_k8s_tool("system_info", {})
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """异步执行"""
        result = await self._execute_k8s_tool_async("system_info", {})
        return json.dumps(result, ensure_ascii=False, indent=2)


def create_langchain_tools(config: Config) -> List[BaseTool]:
    """创建所有 LangChain 工具"""
    if not LANGCHAIN_AVAILABLE:
        print("警告: LangChain 不可用，返回空工具列表")
        return []
    
    return [
        K8sClusterInfoTool(config),
        K8sPodInfoTool(config),
        K8sNodeInfoTool(config),
        K8sEventsTool(config),
        K8sLogsTool(config),
        SystemInfoTool(config)
    ] 