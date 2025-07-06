"""
对话管理模块
"""
from typing import Dict, List, Optional
from ..config import Config
from ..llm.base import Message


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.max_conversation_length = config.max_conversation_length
    
    def format_conversation(self, messages: List[Message]) -> List[Message]:
        """格式化对话，保持在最大长度限制内"""
        if len(messages) <= self.max_conversation_length:
            return messages
        
        # 保留最近的消息
        return messages[-self.max_conversation_length:]
    
    def get_conversation_summary(self, messages: List[Message]) -> str:
        """获取对话摘要"""
        if not messages:
            return "空对话"
        
        user_messages = [msg for msg in messages if msg.role == "user"]
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        
        return f"对话包含 {len(user_messages)} 个用户消息和 {len(assistant_messages)} 个助手回复"
    
    def extract_context(self, messages: List[Message]) -> Dict[str, str]:
        """提取对话上下文"""
        context = {
            "last_user_message": "",
            "last_assistant_message": "",
            "conversation_type": "general"
        }
        
        # 获取最后的用户消息
        for msg in reversed(messages):
            if msg.role == "user" and not context["last_user_message"]:
                context["last_user_message"] = msg.content
            elif msg.role == "assistant" and not context["last_assistant_message"]:
                context["last_assistant_message"] = msg.content
        
        # 判断对话类型
        if any("k8s" in msg.content.lower() or "kubernetes" in msg.content.lower() 
               for msg in messages if msg.role == "user"):
            context["conversation_type"] = "k8s_diagnosis"
        
        return context 