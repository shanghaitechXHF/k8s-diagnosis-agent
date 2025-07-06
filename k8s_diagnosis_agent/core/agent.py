"""
核心Agent类
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
from loguru import logger

from ..config import Config
from ..llm.base import Message, LLMResponse, BaseLLMProvider
from ..llm.factory import LLMFactory
from ..tools.registry import tool_registry
from ..tools.base import ToolResult
from .planner import Planner
from .executor import Executor
from .conversation import ConversationManager
from .session import SessionManager


class Agent:
    """k8s诊断Agent核心类"""
    
    def __init__(self, config: Config):
        """
        初始化Agent
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.llm_provider: Optional[BaseLLMProvider] = None
        self.planner = Planner(config)
        self.executor = Executor(config)
        self.conversation_manager = ConversationManager(config)
        self.session_manager = SessionManager(config)
        
        # 系统提示词
        self.system_prompt = self._create_system_prompt()
        
        # 初始化LLM提供者
        self._init_llm_provider()
    
    def _init_llm_provider(self):
        """初始化LLM提供者"""
        try:
            # 获取默认模型配置
            default_model = self.config.llm.default_model
            
            if default_model.startswith("gpt") or default_model.startswith("openai"):
                provider_config = {
                    "api_key": self.config.llm.openai_api_key,
                    "base_url": self.config.llm.openai_base_url,
                    "model": self.config.llm.openai_model,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "timeout": self.config.llm.timeout
                }
                self.llm_provider = LLMFactory.create_provider("openai", provider_config)
                
            elif default_model.startswith("claude"):
                provider_config = {
                    "api_key": self.config.llm.claude_api_key,
                    "base_url": self.config.llm.claude_base_url,
                    "model": self.config.llm.claude_model,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "timeout": self.config.llm.timeout
                }
                self.llm_provider = LLMFactory.create_provider("claude", provider_config)
                
            elif default_model.startswith("deepseek"):
                provider_config = {
                    "api_key": self.config.llm.deepseek_api_key,
                    "base_url": self.config.llm.deepseek_base_url,
                    "model": self.config.llm.deepseek_model,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "timeout": self.config.llm.timeout
                }
                self.llm_provider = LLMFactory.create_provider("deepseek", provider_config)
                
            else:
                raise ValueError(f"不支持的默认模型: {default_model}")
                
            logger.info(f"已初始化LLM提供者: {default_model}")
            
        except Exception as e:
            logger.error(f"初始化LLM提供者失败: {e}")
            raise
    
    def _create_system_prompt(self) -> str:
        """创建系统提示词"""
        tools_info = tool_registry.list_tools_by_category()
        
        return f"""你是一个专业的Kubernetes集群故障诊断AI助手。你的任务是帮助用户诊断和解决k8s集群中的问题。

你有以下能力：
1. 分析用户的问题，制定诊断计划
2. 使用内置工具收集k8s集群和系统信息
3. 分析收集到的数据，识别问题根因
4. 提供具体的解决方案和建议
5. 支持多轮对话，深入分析问题

可用的工具：
Kubernetes工具: {', '.join(tools_info['kubernetes'])}
系统工具: {', '.join(tools_info['system'])}

工作流程：
1. 理解用户问题
2. 制定诊断计划
3. 执行诊断工具
4. 分析结果
5. 提供解决方案

请始终：
- 使用中文回复
- 保持专业和友好的语气
- 提供具体可行的建议
- 在需要时使用工具收集信息
- 解释你的推理过程

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    async def process_message(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        stream: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        处理用户消息
        
        Args:
            message: 用户消息
            session_id: 会话ID
            stream: 是否流式返回
            
        Yields:
            处理结果
        """
        try:
            # 获取或创建会话
            if not session_id:
                session_id = self.session_manager.create_session()
            session = self.session_manager.get_session(session_id)
            if session is None:
                raise RuntimeError("无法获取会话，请检查session_id")
            
            # 添加用户消息到会话
            user_message = Message(role="user", content=message)
            session.add_message(user_message)
            
            # 制定计划
            plan = await self.planner.create_plan(message, session.get_messages())
            
            # 执行计划
            execution_results = []
            async for result in self.executor.execute_plan(plan):
                execution_results.append(result)
                yield {
                    "type": "execution_step",
                    "data": result,
                    "session_id": session_id
                }
            
            # 生成最终回复
            context = self._build_context(session.get_messages(), execution_results)
            
            if self.llm_provider is None:
                raise RuntimeError("LLM提供者未初始化")
            
            if stream:
                # 流式回复
                response_content = ""
                async for chunk in self.llm_provider.stream_generate(
                    context["messages"],
                    system_prompt=self.system_prompt,
                    tools=context.get("tools")
                ):  # type: ignore
                    response_content += chunk
                    yield {
                        "type": "response_chunk",
                        "data": chunk,
                        "session_id": session_id
                    }
                
                # 添加助手回复到会话
                assistant_message = Message(role="assistant", content=response_content)
                session.add_message(assistant_message)
                
                yield {
                    "type": "response_complete",
                    "data": {
                        "content": response_content,
                        "plan": plan,
                        "execution_results": execution_results
                    },
                    "session_id": session_id
                }
            else:
                # 非流式回复
                response = await self.llm_provider.generate(
                    context["messages"],
                    system_prompt=self.system_prompt,
                    tools=context.get("tools")
                )
                
                # 添加助手回复到会话
                assistant_message = Message(role="assistant", content=response.content)
                session.add_message(assistant_message)
                
                yield {
                    "type": "response_complete",
                    "data": {
                        "content": response.content,
                        "plan": plan,
                        "execution_results": execution_results,
                        "usage": getattr(response, "usage", None)
                    },
                    "session_id": session_id
                }
            
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "message": "处理消息时发生错误"
                },
                "session_id": session_id
            }
    
    def _build_context(self, messages: List[Message], execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建上下文"""
        context_messages = []
        
        # 添加历史消息
        for msg in messages[-10:]:  # 只保留最近10条消息
            context_messages.append(msg)
        
        # 添加执行结果
        if execution_results:
            execution_summary = "工具执行结果：\n"
            for result in execution_results:
                execution_summary += f"- {result.get('tool_name', 'Unknown')}: {result.get('result', {}).get('message', '')}\n"
            
            context_messages.append(Message(role="system", content=execution_summary))
        
        # 添加工具schema
        tools = tool_registry.get_tool_schemas()
        
        return {
            "messages": context_messages,
            "tools": tools
        }
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话历史"""
        session = self.session_manager.get_session(session_id)
        if session is None:
            return []
        return [msg.dict() for msg in session.get_messages()]
    
    async def clear_session(self, session_id: str):
        """清除会话"""
        self.session_manager.remove_session(session_id)
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """获取可用工具信息"""
        return {
            "tools": tool_registry.list_tools_by_category(),
            "schemas": tool_registry.get_tool_schemas()
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """直接执行工具"""
        tool = tool_registry.get_tool(tool_name, self.config.kubernetes.dict())
        return await tool.execute(**kwargs)
    
    def get_llm_info(self) -> Dict[str, Any]:
        """获取当前LLM信息"""
        if self.llm_provider:
            return self.llm_provider.get_model_info()
        return {}
    
    async def switch_llm_provider(self, provider_name: str) -> bool:
        """切换LLM提供者"""
        try:
            # 根据提供者名称创建新的提供者实例
            if provider_name.lower() in ["openai", "gpt"]:
                provider_config = {
                    "api_key": self.config.llm.openai_api_key,
                    "base_url": self.config.llm.openai_base_url,
                    "model": self.config.llm.openai_model,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "timeout": self.config.llm.timeout
                }
                self.llm_provider = LLMFactory.create_provider("openai", provider_config)
                
            elif provider_name.lower() in ["claude", "anthropic"]:
                provider_config = {
                    "api_key": self.config.llm.claude_api_key,
                    "base_url": self.config.llm.claude_base_url,
                    "model": self.config.llm.claude_model,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "timeout": self.config.llm.timeout
                }
                self.llm_provider = LLMFactory.create_provider("claude", provider_config)
                
            elif provider_name.lower() == "deepseek":
                provider_config = {
                    "api_key": self.config.llm.deepseek_api_key,
                    "base_url": self.config.llm.deepseek_base_url,
                    "model": self.config.llm.deepseek_model,
                    "temperature": self.config.llm.temperature,
                    "max_tokens": self.config.llm.max_tokens,
                    "timeout": self.config.llm.timeout
                }
                self.llm_provider = LLMFactory.create_provider("deepseek", provider_config)
                
            else:
                return False
                
            logger.info(f"已切换到LLM提供者: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"切换LLM提供者失败: {e}")
            return False 