"""
AI Agent 智能计划器模块
基于主流 AI Agent planning 思路实现，支持：
- LLM驱动的任务拆分和意图理解
- ReAct设计模式 (Reasoning -> Acting -> Observing)
- 动态TodoList管理
- 任务执行后的效果评估和review
- 自动总结生成
"""
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from ..config import Config
from ..llm.base import Message, BaseLLMProvider
from ..llm.factory import LLMFactory
from ..tools.registry import ToolRegistry
from ..tools.base import ToolResult, ToolStatus


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DiagnosisTask:
    """诊断任务数据类"""
    id: str
    title: str
    description: str
    tool_name: str
    tool_params: Dict[str, Any]
    status: TaskStatus
    priority: TaskPriority
    dependencies: List[str]  # 依赖的任务ID列表
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[ToolResult] = None
    reasoning: str = ""
    expected_outcome: str = ""
    review_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.result:
            data['result'] = {
                'status': self.result.status.value,
                'data': self.result.data,
                'message': self.result.message,
                'error': self.result.error
            }
        return data


class TodoManager:
    """TodoList管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, DiagnosisTask] = {}
        self.execution_order: List[str] = []
    
    def add_task(self, task: DiagnosisTask) -> str:
        """添加任务"""
        self.tasks[task.id] = task
        self._update_execution_order()
        return task.id
    
    def get_task(self, task_id: str) -> Optional[DiagnosisTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Optional[ToolResult] = None):
        """更新任务状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            if status == TaskStatus.IN_PROGRESS:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now()
                if result:
                    task.result = result
    
    def get_next_executable_task(self) -> Optional[DiagnosisTask]:
        """获取下一个可执行的任务"""
        for task_id in self.execution_order:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING and self._are_dependencies_completed(task):
                return task
        return None
    
    def _are_dependencies_completed(self, task: DiagnosisTask) -> bool:
        """检查任务依赖是否已完成"""
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep_task = self.tasks[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    return False
        return True
    
    def _update_execution_order(self):
        """更新执行顺序（简单的拓扑排序）"""
        # 重新计算执行顺序
        pending_tasks = [task_id for task_id, task in self.tasks.items() 
                        if task.status == TaskStatus.PENDING]
        
        ordered = []
        remaining = set(pending_tasks)
        
        while remaining:
            # 找到没有未完成依赖的任务
            ready_tasks = []
            for task_id in remaining:
                task = self.tasks[task_id]
                if all(dep_id not in remaining or dep_id in ordered 
                      for dep_id in task.dependencies):
                    ready_tasks.append(task_id)
            
            if not ready_tasks:
                # 如果没有ready的任务，说明有循环依赖，按优先级排序
                ready_tasks = sorted(remaining, 
                                   key=lambda x: self.tasks[x].priority.value)[:1]
            
            # 按优先级排序ready的任务
            ready_tasks.sort(key=lambda x: (
                self.tasks[x].priority.value,
                self.tasks[x].created_at
            ), reverse=True)
            
            ordered.extend(ready_tasks)
            remaining -= set(ready_tasks)
        
        self.execution_order = ordered
    
    def get_summary(self) -> Dict[str, Any]:
        """获取任务概要"""
        total = len(self.tasks)
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for task in self.tasks.values() 
                                            if task.status == status)
        
        next_task = self.get_next_executable_task()
        return {
            "total_tasks": total,
            "status_distribution": status_counts,
            "completion_rate": status_counts.get("completed", 0) / total if total > 0 else 0,
            "current_task": next_task.id if next_task is not None else None
        }


class AIPlanner:
    """AI智能规划器 - 基于ReAct模式"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_provider: Optional[BaseLLMProvider] = None
        self.tool_registry = ToolRegistry()
        self.todo_manager = TodoManager()
        self.conversation_history: List[Message] = []
        self._init_llm()
    
    def _init_llm(self):
        """初始化LLM提供者"""
        try:
            llm_config = {
                "api_key": self.config.llm.openai_api_key,
                "base_url": self.config.llm.openai_base_url,
                "model": self.config.llm.openai_model,
                "temperature": self.config.llm.temperature,
                "max_tokens": self.config.llm.max_tokens,
                "timeout": self.config.llm.timeout
            }
            provider_name = "openai"  # 默认使用OpenAI
            self.llm_provider = LLMFactory.create_provider(provider_name, llm_config)
        except Exception as e:
            print(f"警告：无法初始化LLM提供者: {e}")
    
    async def create_diagnosis_plan(self, user_message: str, 
                                  conversation_history: List[Message]) -> Dict[str, Any]:
        """创建诊断计划 - 主入口方法"""
        self.conversation_history = conversation_history.copy()
        
        # Phase 1: Reasoning - 理解用户意图并制定计划
        plan_result = await self._reasoning_phase(user_message)
        
        # Phase 2: Acting - 执行任务
        execution_result = await self._acting_phase()
        
        # Phase 3: Observing - 观察结果并生成总结
        final_result = await self._observing_phase()
        
        return {
            "plan": plan_result,
            "execution": execution_result,
            "summary": final_result,
            "todo_summary": self.todo_manager.get_summary()
        }
    
    async def _reasoning_phase(self, user_message: str) -> Dict[str, Any]:
        """推理阶段：理解用户意图并拆分任务"""
        if not self.llm_provider:
            # 降级到简单的关键词匹配
            return await self._fallback_planning(user_message)
        
        # 构建任务拆分提示
        system_prompt = self._get_planning_system_prompt()
        
        # 添加用户消息到历史
        self.conversation_history.append(Message(role="user", content=user_message))
        
        try:
            # 调用LLM进行任务拆分
            response = await self.llm_provider.generate(
                messages=self.conversation_history,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # 解析LLM响应，生成任务列表
            tasks = await self._parse_llm_plan_response(response.content, user_message)
            
            # 添加任务到TodoManager
            task_ids = []
            for task_data in tasks:
                task = DiagnosisTask(
                    id=str(uuid.uuid4()),
                    title=task_data["title"],
                    description=task_data["description"],
                    tool_name=task_data["tool_name"],
                    tool_params=task_data["tool_params"],
                    status=TaskStatus.PENDING,
                    priority=TaskPriority(task_data.get("priority", "medium")),
                    dependencies=task_data.get("dependencies", []),
                    reasoning=task_data.get("reasoning", ""),
                    expected_outcome=task_data.get("expected_outcome", ""),
                    created_at=datetime.now()
                )
                task_id = self.todo_manager.add_task(task)
                task_ids.append(task_id)
            
            return {
                "reasoning": response.content,
                "tasks_created": len(tasks),
                "task_ids": task_ids,
                "method": "llm_planning"
            }
            
        except Exception as e:
            print(f"LLM规划失败，使用降级方案: {e}")
            return await self._fallback_planning(user_message)
    
    async def _acting_phase(self) -> Dict[str, Any]:
        """执行阶段：按顺序执行任务"""
        execution_log = []
        completed_tasks = 0
        failed_tasks = 0
        
        while True:
            # 获取下一个可执行任务
            next_task = self.todo_manager.get_next_executable_task()
            if not next_task:
                break
            
            # 更新任务状态为执行中
            self.todo_manager.update_task_status(next_task.id, TaskStatus.IN_PROGRESS)
            
            # 执行任务
            result = await self._execute_task(next_task)
            
            # 更新任务状态
            if result.status == ToolStatus.SUCCESS:
                self.todo_manager.update_task_status(next_task.id, TaskStatus.COMPLETED, result)
                completed_tasks += 1
                
                # 执行后评估（ReAct的Observing部分）
                review_result = await self._review_task_result(next_task, result)
                next_task.review_notes = review_result
                
            else:
                self.todo_manager.update_task_status(next_task.id, TaskStatus.FAILED, result)
                failed_tasks += 1
            
            execution_log.append({
                "task_id": next_task.id,
                "task_title": next_task.title,
                "status": next_task.status.value,
                "execution_time": datetime.now().isoformat(),
                "result_summary": result.message
            })
        
        return {
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "execution_log": execution_log
        }
    
    async def _observing_phase(self) -> Dict[str, Any]:
        """观察阶段：生成总结和最终报告"""
        if not self.llm_provider:
            return self._generate_simple_summary()
        
        # 收集所有任务结果
        task_results = []
        for task in self.todo_manager.tasks.values():
            task_results.append({
                "title": task.title,
                "status": task.status.value,
                "result": task.result.data if task.result else None,
                "review": task.review_notes
            })
        
        # 使用LLM生成总结
        summary_prompt = self._get_summary_system_prompt()
        summary_input = json.dumps(task_results, ensure_ascii=False, indent=2)
        
        try:
            response = await self.llm_provider.generate(
                messages=[Message(role="user", content=f"请为以下诊断结果生成总结:\n{summary_input}")],
                system_prompt=summary_prompt,
                temperature=0.1
            )
            
            return {
                "summary": response.content,
                "task_count": len(task_results),
                "success_rate": sum(1 for t in task_results if t["status"] == "completed") / len(task_results) if task_results else 0,
                "method": "llm_summary"
            }
            
        except Exception as e:
            print(f"LLM总结失败，使用简单总结: {e}")
            return self._generate_simple_summary()
    
    async def _execute_task(self, task: DiagnosisTask) -> ToolResult:
        """执行单个任务"""
        try:
            tool = self.tool_registry.get_tool(task.tool_name)
            result = await tool.execute(**task.tool_params)
            return result
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"执行任务 {task.title} 失败"
            )
    
    async def _review_task_result(self, task: DiagnosisTask, result: ToolResult) -> str:
        """评估任务执行结果"""
        if not self.llm_provider:
            return f"任务完成，状态: {result.status.value}"
        
        try:
            review_prompt = f"""
            任务: {task.title}
            期望结果: {task.expected_outcome}
            实际结果: {result.message}
            数据: {json.dumps(result.data, ensure_ascii=False) if result.data else "无"}
            
            请评估这个任务是否达到了预期效果，并提供简短的评价。
            """
            
            response = await self.llm_provider.generate(
                messages=[Message(role="user", content=review_prompt)],
                system_prompt="你是一个Kubernetes诊断专家，请简短评估任务完成情况。",
                temperature=0.1
            )
            
            return response.content
            
        except Exception as e:
            return f"自动评估失败: {e}"
    
    async def _parse_llm_plan_response(self, llm_response: str, user_message: str) -> List[Dict[str, Any]]:
        """解析LLM的规划响应"""
        # 尝试从LLM响应中解析JSON格式的任务列表
        try:
            # 如果LLM返回JSON格式
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                json_str = llm_response[json_start:json_end].strip()
                tasks_data = json.loads(json_str)
                return tasks_data.get("tasks", [])
            
            # 否则使用规则解析或降级
            return await self._fallback_task_extraction(user_message)
            
        except Exception as e:
            print(f"解析LLM响应失败: {e}")
            return await self._fallback_task_extraction(user_message)
    
    async def _fallback_planning(self, user_message: str) -> Dict[str, Any]:
        """降级规划方案"""
        tasks = await self._fallback_task_extraction(user_message)
        
        task_ids = []
        for task_data in tasks:
            task = DiagnosisTask(
                id=str(uuid.uuid4()),
                title=task_data["title"],
                description=task_data["description"],
                tool_name=task_data["tool_name"],
                tool_params=task_data["tool_params"],
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                dependencies=[],
                reasoning="基于关键词匹配生成",
                expected_outcome=task_data["description"],
                created_at=datetime.now()
            )
            task_id = self.todo_manager.add_task(task)
            task_ids.append(task_id)
        
        return {
            "reasoning": f"基于关键词匹配为 '{user_message}' 创建的诊断计划",
            "tasks_created": len(tasks),
            "task_ids": task_ids,
            "method": "keyword_matching"
        }
    
    async def _fallback_task_extraction(self, user_message: str) -> List[Dict[str, Any]]:
        """降级任务提取（关键词匹配）"""
        tasks = []
        message_lower = user_message.lower()
        
        # 总是先获取集群信息
        tasks.append({
            "title": "获取集群基本信息",
            "description": "获取Kubernetes集群的基本信息和状态",
            "tool_name": "k8s_cluster_info",
            "tool_params": {}
        })
        
        # 基于关键词添加相应任务
        if any(keyword in message_lower for keyword in ["pod", "容器", "应用"]):
            tasks.append({
                "title": "获取Pod信息",
                "description": "获取Pod的详细信息和状态",
                "tool_name": "k8s_pod_info",
                "tool_params": {}
            })
        
        if any(keyword in message_lower for keyword in ["node", "节点"]):
            tasks.append({
                "title": "获取节点信息",
                "description": "获取集群节点的详细信息",
                "tool_name": "k8s_node_info",
                "tool_params": {}
            })
        
        if any(keyword in message_lower for keyword in ["service", "服务"]):
            tasks.append({
                "title": "获取服务信息",
                "description": "获取Kubernetes服务信息",
                "tool_name": "k8s_service_info",
                "tool_params": {}
            })
        
        if any(keyword in message_lower for keyword in ["event", "事件", "错误"]):
            tasks.append({
                "title": "获取事件信息",
                "description": "获取集群事件和错误信息",
                "tool_name": "k8s_events",
                "tool_params": {}
            })
        
        if any(keyword in message_lower for keyword in ["log", "日志"]):
            tasks.append({
                "title": "获取日志信息",
                "description": "获取Pod日志信息",
                "tool_name": "k8s_logs",
                "tool_params": {}
            })
        
        if any(keyword in message_lower for keyword in ["system", "系统"]):
            tasks.append({
                "title": "获取系统信息",
                "description": "获取系统资源和性能信息",
                "tool_name": "system_info",
                "tool_params": {}
            })
        
        return tasks
    
    def _generate_simple_summary(self) -> Dict[str, Any]:
        """生成简单总结"""
        summary = self.todo_manager.get_summary()
        
        completed_tasks = [task for task in self.todo_manager.tasks.values() 
                          if task.status == TaskStatus.COMPLETED]
        
        summary_text = f"""
        诊断任务执行完成。
        
        总任务数: {summary['total_tasks']}
        完成任务数: {summary['status_distribution'].get('completed', 0)}
        失败任务数: {summary['status_distribution'].get('failed', 0)}
        完成率: {summary['completion_rate']:.2%}
        
        主要发现:
        """
        
        for task in completed_tasks[:3]:  # 显示前3个完成的任务
            if task.result and task.result.data:
                summary_text += f"\n- {task.title}: {task.result.message}"
        
        return {
            "summary": summary_text,
            "task_count": summary['total_tasks'],
            "success_rate": summary['completion_rate'],
            "method": "simple_summary"
        }
    
    def _get_planning_system_prompt(self) -> str:
        """获取任务规划的系统提示"""
        available_tools = self.tool_registry.get_tool_schemas()
        tools_info = json.dumps(available_tools, ensure_ascii=False, indent=2)
        
        return f"""你是一个专业的Kubernetes诊断专家。根据用户的问题，你需要将其拆分为一系列具体的诊断任务。

可用工具:
{tools_info}

请按以下JSON格式返回任务列表:
```json
{{
  "tasks": [
    {{
      "title": "任务标题",
      "description": "详细描述",
      "tool_name": "工具名称",
      "tool_params": {{}},
      "priority": "high|medium|low",
      "dependencies": [],
      "reasoning": "选择此任务的原因",
      "expected_outcome": "期望的结果"
    }}
  ]
}}
```

原则:
1. 优先获取基础信息（集群、节点状态）
2. 根据问题类型选择合适的诊断工具
3. 考虑任务之间的依赖关系
4. 每个任务都要有明确的目标和期望结果"""
    
    def _get_summary_system_prompt(self) -> str:
        """获取总结生成的系统提示"""
        return """你是一个Kubernetes诊断专家。请基于诊断任务的执行结果，生成一份专业的诊断总结报告。

报告应包含:
1. 诊断概述
2. 发现的问题（如果有）
3. 系统状态评估
4. 建议的解决方案（如果需要）
5. 总结

请使用专业但易懂的语言，突出重点发现和关键信息。"""


# 保留原有接口兼容性
class DiagnosisPlan:
    """诊断计划 - 兼容性包装器"""
    
    def __init__(self, steps: List[Dict[str, Any]], reasoning: str = ""):
        self.steps = steps
        self.reasoning = reasoning
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat()
        }


class Planner:
    """计划器 - 兼容性包装器"""
    
    def __init__(self, config: Config):
        self.ai_planner = AIPlanner(config)
    
    async def create_plan(self, user_message: str, conversation_history: List[Message]) -> DiagnosisPlan:
        """创建诊断计划 - 兼容接口"""
        result = await self.ai_planner.create_diagnosis_plan(user_message, conversation_history)
        
        # 转换为原有格式
        steps = []
        for task_id in result["plan"]["task_ids"]:
            task = self.ai_planner.todo_manager.get_task(task_id)
            if task:
                steps.append({
                    "tool": task.tool_name,
                    "params": task.tool_params,
                    "description": task.description
                })
        
        return DiagnosisPlan(
            steps=steps,
            reasoning=result["plan"]["reasoning"]
        ) 