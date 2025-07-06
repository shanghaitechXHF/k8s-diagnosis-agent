"""
Web API路由
"""
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from datetime import datetime
import json

from ..core import Agent
from ..config import config
from .models import ChatRequest, ChatResponse, ToolRequest, ToolResponse, SessionInfo, SystemStatus

router = APIRouter()

# 全局Agent实例
agent = Agent(config)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        if request.stream:
            # 流式响应
            async def generate():
                async for result in agent.process_message(
                    request.message, 
                    request.session_id, 
                    stream=True
                ):
                    yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(generate(), media_type="text/plain")
        else:
            # 非流式响应
            results = []
            async for result in agent.process_message(
                request.message, 
                request.session_id, 
                stream=False
            ):
                results.append(result)
            
            # 返回最后的完整响应
            final_result = results[-1] if results else {"type": "error", "data": {"message": "没有响应"}}
            return ChatResponse(**final_result)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tool", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):
    """执行工具接口"""
    try:
        result = await agent.execute_tool(request.tool_name, **request.params)
        
        return ToolResponse(
            tool_name=request.tool_name,
            success=result.is_success(),
            result=result.to_dict(),
            message=result.message
        )
        
    except Exception as e:
        return ToolResponse(
            tool_name=request.tool_name,
            success=False,
            result={"error": str(e)},
            message=f"执行工具失败: {str(e)}"
        )


@router.get("/tools")
async def get_available_tools():
    """获取可用工具列表"""
    try:
        tools = await agent.get_available_tools()
        return tools
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史"""
    try:
        history = await agent.get_session_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除会话"""
    try:
        await agent.clear_session(session_id)
        return {"message": "会话已清除", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_sessions():
    """获取所有会话"""
    try:
        sessions = agent.session_manager.get_all_sessions()
        session_info = []
        
        for session_id in sessions:
            session = agent.session_manager.get_session(session_id)
            if session:
                session_info.append(SessionInfo(
                    session_id=session_id,
                    created_at=session.created_at.isoformat(),
                    last_activity=session.last_activity.isoformat(),
                    message_count=len(session.messages)
                ))
        
        return {"sessions": session_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """获取系统状态"""
    try:
        llm_info = agent.get_llm_info()
        tools = await agent.get_available_tools()
        
        return SystemStatus(
            status="running",
            llm_provider=llm_info.get("provider", "unknown"),
            available_tools=list(tools.get("tools", {}).keys()),
            session_count=agent.session_manager.get_session_count(),
            version=config.version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/model/switch")
async def switch_model(provider: str):
    """切换模型"""
    try:
        success = await agent.switch_llm_provider(provider)
        if success:
            return {"message": f"已切换到 {provider}", "success": True}
        else:
            return {"message": f"切换到 {provider} 失败", "success": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()} 