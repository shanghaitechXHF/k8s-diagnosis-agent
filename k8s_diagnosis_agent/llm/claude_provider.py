"""
Claude LLM提供者实现
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
import httpx
from .base import BaseLLMProvider, Message, LLMResponse


class ClaudeProvider(BaseLLMProvider):
    """Claude LLM提供者"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.anthropic.com")
        self.model_name = config.get("model", "claude-3-opus-20240229")
        headers = {
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout
        )
    
    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """生成响应"""
        try:
            formatted_messages = self.format_messages(messages)
            
            request_data = {
                "model": self.model_name,
                "messages": formatted_messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }
            
            if system_prompt:
                request_data["system"] = system_prompt
            
            response = await self.client.post("/v1/messages", json=request_data)
            response.raise_for_status()
            
            result = response.json()
            
            return LLMResponse(
                content=result["content"][0]["text"],
                model=result["model"],
                usage=result.get("usage", {}),
                metadata={"response_id": result.get("id"), "type": result.get("type")}
            )
            
        except Exception as e:
            raise Exception(f"Claude API调用失败: {str(e)}")
    
    async def stream_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        try:
            formatted_messages = self.format_messages(messages)
            
            request_data = {
                "model": self.model_name,
                "messages": formatted_messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "stream": True,
            }
            
            if system_prompt:
                request_data["system"] = system_prompt
            
            async with self.client.stream("POST", "/v1/messages", json=request_data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                if chunk["delta"].get("text"):
                                    yield chunk["delta"]["text"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            raise Exception(f"Claude流式API调用失败: {str(e)}")
    
    async def embed(self, text: str) -> List[float]:
        """文本嵌入 - Claude暂不支持，抛出异常"""
        raise NotImplementedError("Claude暂不支持文本嵌入功能")
    
    def supports_function_calling(self) -> bool:
        """是否支持函数调用"""
        return True  # Claude 3支持工具调用
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "claude",
            "model": self.model_name,
            "supports_function_calling": self.supports_function_calling(),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
    
    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose() 