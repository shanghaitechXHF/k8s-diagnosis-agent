"""
执行器模块
"""
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from ..config import Config
from ..tools.registry import tool_registry
from .planner import DiagnosisPlan


class Executor:
    """执行器"""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def execute_plan(self, plan: DiagnosisPlan) -> AsyncIterator[Dict[str, Any]]:
        """执行诊断计划"""
        for step in plan.steps:
            try:
                # 获取工具
                tool_name = step["tool"]
                tool_params = step.get("params", {})
                
                # 创建工具实例
                tool = tool_registry.get_tool(tool_name, self.config.kubernetes.__dict__)
                
                # 执行工具
                result = await tool.execute(**tool_params)
                
                yield {
                    "tool_name": tool_name,
                    "description": step.get("description", ""),
                    "result": result.to_dict(),
                    "success": result.is_success()
                }
                
            except Exception as e:
                yield {
                    "tool_name": step.get("tool", "unknown"),
                    "description": step.get("description", ""),
                    "result": {
                        "status": "error",
                        "error": str(e),
                        "message": f"执行工具失败: {str(e)}"
                    },
                    "success": False
                }
    
    async def execute_single_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行单个工具"""
        try:
            tool = tool_registry.get_tool(tool_name, self.config.kubernetes.__dict__)
            result = await tool.execute(**kwargs)
            
            return {
                "tool_name": tool_name,
                "result": result.to_dict(),
                "success": result.is_success()
            }
            
        except Exception as e:
            return {
                "tool_name": tool_name,
                "result": {
                    "status": "error",
                    "error": str(e),
                    "message": f"执行工具失败: {str(e)}"
                },
                "success": False
            } 