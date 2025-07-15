"""
基于 LangChain 的 K8s 诊断 Agent
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

# 注意：这些导入在实际环境中需要安装相应的包
# 这里使用 try-except 来处理可能的导入错误
try:
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain.agents.format_scratchpad import format_log_to_messages
    from langchain.agents.output_parsers import ReActSingleInputOutputParser
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_community.llms import DeepSeek
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"警告: LangChain 导入失败: {e}")
    # 如果 LangChain 不可用，创建模拟类
    class AgentExecutor:
        def __init__(self, agent=None, tools=None, memory=None, verbose=True, 
                     handle_parsing_errors=True, max_iterations=10, return_intermediate_steps=True):
            self.agent = agent
            self.tools = tools
            self.memory = memory
            self.verbose = verbose
        
        async def ainvoke(self, inputs):
            return {"output": "LangChain not available", "intermediate_steps": []}
        
        async def astream(self, inputs):
            yield {"output": "LangChain not available"}
    
    def create_react_agent(llm, tools, prompt):
        return None
    
    class BaseMessage:
        def __init__(self, content: str, type: str = "human"):
            self.content = content
            self.type = type
    
    class HumanMessage(BaseMessage):
        def __init__(self, content: str):
            super().__init__(content, "human")
    
    class AIMessage(BaseMessage):
        def __init__(self, content: str):
            super().__init__(content, "ai")
    
    class ChatOpenAI:
        def __init__(self, **kwargs):
            pass
    
    class ChatAnthropic:
        def __init__(self, **kwargs):
            pass
    
    class DeepSeek:
        def __init__(self, **kwargs):
            pass
    
    LANGCHAIN_AVAILABLE = False

from ..config import Config
from .tools import create_langchain_tools
from .memory import K8sDiagnosisMemory
from .chains import DiagnosisChain, K8sAnalysisChain, K8sSummaryChain
from .prompts import K8sPromptManager


class K8sDiagnosisAgent:
    """基于 LangChain 的 K8s 诊断 Agent"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = self._create_langchain_llm()
        self.tools = create_langchain_tools(config)
        self.memory = K8sDiagnosisMemory(config)
        self.prompt_manager = K8sPromptManager(config)
        
        # 创建 ReAct Agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt_manager.get_agent_prompt()
        )
        
        # 创建 AgentExecutor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory.short_term_memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            return_intermediate_steps=True
        )
    
    def _create_langchain_llm(self):
        """创建 LangChain LLM 实例"""
        default_model = self.config.llm.default_model
        
        if default_model.startswith("gpt") or default_model.startswith("openai"):
            return ChatOpenAI(
                api_key=self.config.llm.openai_api_key,
                base_url=self.config.llm.openai_base_url,
                model=self.config.llm.openai_model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
                timeout=self.config.llm.timeout
            )
        elif default_model.startswith("claude"):
            return ChatAnthropic(
                api_key=self.config.llm.claude_api_key,
                model=self.config.llm.claude_model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
        elif default_model.startswith("deepseek"):
            return DeepSeek(
                api_key=self.config.llm.deepseek_api_key,
                model=self.config.llm.deepseek_model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
        else:
            raise ValueError(f"不支持的默认模型: {default_model}")
    
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
            # 获取相关历史记录
            relevant_history = self.memory.get_relevant_history(message)
            
            # 构建上下文
            context = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "relevant_history": relevant_history
            }
            
            # 执行 Agent
            if stream:
                # 流式执行
                async for chunk in self._stream_execute(message, context):
                    yield chunk
            else:
                # 非流式执行
                result = await self._execute(message, context)
                yield {
                    "type": "response_complete",
                    "data": result,
                    "session_id": session_id
                }
            
            # 保存交互到记忆系统
            self.memory.add_interaction(message, result.get("output", ""), context)
            
        except Exception as e:
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "message": "处理消息时发生错误"
                },
                "session_id": session_id
            }
    
    async def _execute(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent"""
        try:
            # 构建输入
            inputs = {
                "input": message,
                "chat_history": self.memory.short_term_memory.chat_memory.messages
            }
            
            # 执行 Agent
            result = await self.agent_executor.ainvoke(inputs)
            
            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
                "context": context,
                "execution_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "output": f"执行失败: {str(e)}",
                "error": str(e),
                "context": context,
                "execution_time": datetime.now().isoformat()
            }
    
    async def _stream_execute(self, message: str, context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """流式执行 Agent"""
        try:
            # 构建输入
            inputs = {
                "input": message,
                "chat_history": self.memory.short_term_memory.chat_memory.messages
            }
            
            # 流式执行
            async for chunk in self.agent_executor.astream(inputs):
                if "output" in chunk:
                    yield {
                        "type": "response_chunk",
                        "data": chunk["output"],
                        "session_id": context.get("session_id")
                    }
                elif "intermediate_steps" in chunk:
                    yield {
                        "type": "execution_step",
                        "data": {
                            "steps": chunk["intermediate_steps"],
                            "context": context
                        },
                        "session_id": context.get("session_id")
                    }
            
            # 最终结果
            final_result = await self._execute(message, context)
            yield {
                "type": "response_complete",
                "data": final_result,
                "session_id": context.get("session_id")
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "message": "流式执行失败"
                },
                "session_id": context.get("session_id")
            }
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话历史"""
        messages = self.memory.short_term_memory.chat_memory.messages
        return [
            {
                "role": msg.type,
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            }
            for msg in messages
        ]
    
    async def clear_session(self, session_id: str):
        """清除会话"""
        self.memory.short_term_memory.chat_memory.clear()
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """获取可用工具信息"""
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": tool.args_schema.schema() if tool.args_schema else None
                }
                for tool in self.tools
            ]
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """直接执行工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    result = await tool._arun(**kwargs)
                    return {
                        "tool_name": tool_name,
                        "result": result,
                        "success": True
                    }
                except Exception as e:
                    return {
                        "tool_name": tool_name,
                        "result": f"执行失败: {str(e)}",
                        "success": False
                    }
        
        return {
            "tool_name": tool_name,
            "result": f"工具 {tool_name} 不存在",
            "success": False
        }
    
    def get_llm_info(self) -> Dict[str, Any]:
        """获取当前 LLM 信息"""
        try:
            model_name = getattr(self.llm, 'model_name', None)
            if model_name is None:
                model_name = getattr(self.llm, 'model', None)
            if model_name is None:
                model_name = str(type(self.llm).__name__)
            
            return {
                "model": model_name,
                "temperature": getattr(self.llm, 'temperature', None),
                "max_tokens": getattr(self.llm, 'max_tokens', None),
                "llm_type": type(self.llm).__name__
            }
        except Exception as e:
            return {
                "model": "Unknown",
                "temperature": None,
                "max_tokens": None,
                "error": str(e)
            }
    
    async def get_diagnosis_summary(self, session_id: str) -> Dict[str, Any]:
        """获取诊断总结"""
        try:
            # 获取会话历史
            messages = self.memory.short_term_memory.chat_memory.messages
            
            if not messages:
                return {"summary": "无诊断历史"}
            
            # 构建总结提示
            conversation_text = "\n".join([
                f"{msg.type}: {msg.content}" for msg in messages[-10:]  # 最近10条消息
            ])
            
            summary_prompt = f"""
            请为以下Kubernetes诊断对话生成总结：
            
            {conversation_text}
            
            总结应包含：
            1. 诊断的主要问题
            2. 执行的诊断步骤
            3. 发现的关键信息
            4. 建议的解决方案
            """
            
            # 生成总结
            try:
                if hasattr(self.llm, 'ainvoke'):
                    result = await self.llm.ainvoke([HumanMessage(content=summary_prompt)])
                    summary = result.content if hasattr(result, 'content') else str(result)
                else:
                    # 如果 LLM 不支持异步调用，使用同步方法
                    summary = "LLM 不支持异步调用，无法生成总结"
                
                return {
                    "summary": summary,
                    "session_id": session_id,
                    "message_count": len(messages),
                    "generated_at": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "summary": f"生成总结失败: {str(e)}",
                    "session_id": session_id,
                    "message_count": len(messages),
                    "generated_at": datetime.now().isoformat(),
                    "error": str(e)
                }
            
        except Exception as e:
            return {
                "summary": f"生成总结失败: {str(e)}",
                "session_id": session_id,
                "error": str(e)
            } 