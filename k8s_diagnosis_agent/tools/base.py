"""
工具基础抽象类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class ToolStatus(Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ToolResult:
    """工具执行结果"""
    
    def __init__(
        self,
        status: ToolStatus,
        data: Any = None,
        message: str = "",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.data = data
        self.message = message
        self.error = error
        self.metadata = metadata or {}
    
    def is_success(self) -> bool:
        """是否执行成功"""
        return self.status == ToolStatus.SUCCESS
    
    def is_error(self) -> bool:
        """是否执行失败"""
        return self.status == ToolStatus.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """工具基础抽象类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化工具
        
        Args:
            config: 工具配置
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.description = self.__doc__ or ""
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 执行参数
            
        Returns:
            工具执行结果
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具的JSON Schema
        
        Returns:
            工具的JSON Schema
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        验证参数
        
        Args:
            params: 参数字典
            
        Returns:
            参数是否有效
        """
        return True
    
    def get_name(self) -> str:
        """获取工具名称"""
        return self.name
    
    def get_description(self) -> str:
        """获取工具描述"""
        return self.description
    
    def get_config(self) -> Dict[str, Any]:
        """获取工具配置"""
        return self.config
    
    def update_config(self, config: Dict[str, Any]):
        """更新工具配置"""
        self.config.update(config)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        pass 