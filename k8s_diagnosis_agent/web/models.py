"""
Web服务数据模型
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None
    stream: bool = False
    model: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    type: str
    data: Dict[str, Any]
    session_id: str
    timestamp: Optional[str] = None


class ToolRequest(BaseModel):
    """工具请求模型"""
    tool_name: str
    params: Dict[str, Any] = {}


class ToolResponse(BaseModel):
    """工具响应模型"""
    tool_name: str
    success: bool
    result: Dict[str, Any]
    message: str = ""


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str
    created_at: str
    last_activity: str
    message_count: int


class SystemStatus(BaseModel):
    """系统状态模型"""
    status: str
    llm_provider: str
    available_tools: List[str]
    session_count: int
    version: str 