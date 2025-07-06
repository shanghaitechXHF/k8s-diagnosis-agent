"""
计划器模块
"""
import json
from typing import Dict, Any, List, Optional
from ..config import Config
from ..llm.base import Message


class DiagnosisPlan:
    """诊断计划"""
    
    def __init__(self, steps: List[Dict[str, Any]], reasoning: str = ""):
        self.steps = steps
        self.reasoning = reasoning
        self.created_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "reasoning": self.reasoning,
            "created_at": self.created_at
        }


class Planner:
    """计划器"""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def create_plan(self, user_message: str, conversation_history: List[Message]) -> DiagnosisPlan:
        """创建诊断计划"""
        # 简化版本：基于关键词匹配创建计划
        steps = []
        
        # 分析用户消息中的关键词
        message_lower = user_message.lower()
        
        # 总是先获取集群信息
        steps.append({
            "tool": "k8s_cluster_info",
            "params": {},
            "description": "获取集群基本信息"
        })
        
        # 根据关键词添加相应的步骤
        if any(keyword in message_lower for keyword in ["pod", "容器", "应用"]):
            steps.append({
                "tool": "k8s_pod_info",
                "params": {},
                "description": "获取Pod信息"
            })
        
        if any(keyword in message_lower for keyword in ["node", "节点"]):
            steps.append({
                "tool": "k8s_node_info",
                "params": {},
                "description": "获取节点信息"
            })
        
        if any(keyword in message_lower for keyword in ["service", "服务"]):
            steps.append({
                "tool": "k8s_service_info",
                "params": {},
                "description": "获取服务信息"
            })
        
        if any(keyword in message_lower for keyword in ["event", "事件", "错误"]):
            steps.append({
                "tool": "k8s_events",
                "params": {},
                "description": "获取事件信息"
            })
        
        if any(keyword in message_lower for keyword in ["log", "日志"]):
            steps.append({
                "tool": "k8s_logs",
                "params": {},
                "description": "获取日志信息"
            })
        
        if any(keyword in message_lower for keyword in ["system", "系统"]):
            steps.append({
                "tool": "system_info",
                "params": {},
                "description": "获取系统信息"
            })
        
        return DiagnosisPlan(
            steps=steps,
            reasoning=f"基于用户问题 '{user_message}' 创建的诊断计划"
        ) 