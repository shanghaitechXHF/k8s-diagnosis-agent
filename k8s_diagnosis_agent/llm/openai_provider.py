"""
OpenAI LLM提供者实现
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
import httpx
from .base import BaseLLMProvider, Message, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM提供者"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model_name = config.get("model", "gpt-4-turbo")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
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
            
            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})
            
            request_data = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            
            # 添加函数调用支持
            if "tools" in kwargs:
                request_data["tools"] = kwargs["tools"]
                request_data["tool_choice"] = kwargs.get("tool_choice", "auto")
            
            response = await self.client.post("/chat/completions", json=request_data)
            response.raise_for_status()
            
            result = response.json()
            
            return LLMResponse(
                content=result["choices"][0]["message"]["content"],
                model=result["model"],
                usage=result.get("usage", {}),
                metadata={"response_id": result.get("id"), "created": result.get("created")}
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")
    
    async def stream_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成响应"""
        try:
            formatted_messages = self.format_messages(messages)
            
            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})
            
            request_data = {
                "model": self.model_name,
                "messages": formatted_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": True,
            }
            
            async with self.client.stream("POST", "/chat/completions", json=request_data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if chunk["choices"][0]["delta"].get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            raise Exception(f"OpenAI流式API调用失败: {str(e)}")
    
    async def embed(self, text: str) -> List[float]:
        """文本嵌入"""
        try:
            request_data = {
                "model": "text-embedding-3-small",
                "input": text,
            }
            
            response = await self.client.post("/embeddings", json=request_data)
            response.raise_for_status()
            
            result = response.json()
            return result["data"][0]["embedding"]
            
        except Exception as e:
            raise Exception(f"OpenAI嵌入API调用失败: {str(e)}")
    
    def supports_function_calling(self) -> bool:
        """是否支持函数调用"""
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "openai",
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