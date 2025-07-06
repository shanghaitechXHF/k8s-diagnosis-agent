"""
LLM工厂类
"""
from typing import Dict, Any, Type
from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .deepseek_provider import DeepSeekProvider


class LLMFactory:
    """LLM提供者工厂类"""
    
    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIProvider,
        "gpt": OpenAIProvider,  # 别名
        "claude": ClaudeProvider,
        "anthropic": ClaudeProvider,  # 别名
        "deepseek": DeepSeekProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, config: Dict[str, Any]) -> BaseLLMProvider:
        """创建LLM提供者实例"""
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            raise ValueError(f"不支持的LLM提供者: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """获取支持的提供者列表"""
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]):
        """注册新的LLM提供者"""
        cls._providers[name.lower()] = provider_class 