"""
会话管理模块
"""
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..config import Config
from ..llm.base import Message


class Session:
    """会话类"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Message] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.metadata: Dict[str, str] = {}
    
    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_messages(self) -> List[Message]:
        """获取消息列表"""
        return self.messages
    
    def clear_messages(self):
        """清空消息"""
        self.messages.clear()
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_activity > timedelta(seconds=timeout_seconds)


class SessionManager:
    """会话管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, Session] = {}
    
    def create_session(self) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        timeout = self.config.session_timeout
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired(timeout)
        ]
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
    
    def get_all_sessions(self) -> List[str]:
        """获取所有会话ID"""
        return list(self.sessions.keys())
    
    def get_session_count(self) -> int:
        """获取会话数量"""
        return len(self.sessions) 