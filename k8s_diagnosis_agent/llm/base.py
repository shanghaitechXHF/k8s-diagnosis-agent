"""
LLM提供者基础抽象类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from pydantic import BaseModel


class Message(BaseModel):
    """消息模型"""
    role: str
    content: str
    timestamp: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM响应模型"""
    content: str
    model: str
    usage: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class BaseLLMProvider(ABC):
    """LLM提供者基础抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM提供者
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.model_name = config.get("model", "")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)
        self.timeout = config.get("timeout", 60)
        
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成响应
        
        Args:
            messages: 消息列表
            system_prompt: 系统提示
            **kwargs: 其他参数
            
        Returns:
            LLM响应
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成响应
        
        Args:
            messages: 消息列表
            system_prompt: 系统提示
            **kwargs: 其他参数
            
        Yields:
            响应内容片段
        """
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        文本嵌入
        
        Args:
            text: 待嵌入的文本
            
        Returns:
            嵌入向量
        """
        pass
    
    @abstractmethod
    def supports_function_calling(self) -> bool:
        """
        是否支持函数调用
        
        Returns:
            是否支持
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        pass
    
    def format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        格式化消息为API所需格式
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的消息列表
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def validate_config(self) -> bool:
        """
        验证配置
        
        Returns:
            配置是否有效
        """
        required_fields = ["api_key"]
        for field in required_fields:
            if field not in self.config or not self.config[field]:
                return False
        return True 