# LangChain 优化方案

## 当前架构分析

### 现有优势
1. **完整的工具系统**: 已实现 K8s 和系统诊断工具
2. **多LLM支持**: 支持 OpenAI、Claude、DeepSeek
3. **ReAct模式**: 已实现 Reasoning -> Acting -> Observing 循环
4. **会话管理**: 完整的会话和对话管理
5. **配置系统**: 灵活的配置管理

### 可优化点
1. **Agent框架标准化**: 使用 LangChain 的 Agent 框架
2. **工具集成优化**: 利用 LangChain 的 Tool 抽象
3. **记忆系统增强**: 使用 LangChain 的 Memory 组件
4. **链式调用**: 利用 LangChain 的 Chain 和 LCEL
5. **向量存储**: 集成 LangChain 的 VectorStore
6. **提示词管理**: 使用 LangChain 的 PromptTemplate

## LangChain 优化方案

### 1. 核心架构重构

```python
# 新的架构层次
k8s_diagnosis_agent/
├── langchain_agent/           # LangChain Agent 实现
│   ├── __init__.py
│   ├── agent.py              # 主 Agent 类
│   ├── tools.py              # LangChain Tool 包装器
│   ├── memory.py             # 记忆系统
│   ├── chains.py             # 自定义 Chain
│   └── prompts.py            # 提示词模板
├── llm/                      # 保留现有 LLM 接口
├── tools/                    # 保留现有工具实现
└── core/                     # 保留兼容性接口
```

### 2. 具体优化内容

#### 2.1 Agent 框架标准化

**当前问题**: 自定义的 ReAct 实现，缺乏标准化
**LangChain 解决方案**: 使用 `AgentExecutor` + `ReActAgent`

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.format_scratchpad import format_log_to_messages
from langchain.agents.output_parsers import ReActSingleInputOutputParser

class K8sDiagnosisAgent:
    def __init__(self, config: Config):
        self.config = config
        self.llm = self._create_langchain_llm()
        self.tools = self._create_langchain_tools()
        self.memory = self._create_memory()
        
        # 创建 ReAct Agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self._create_agent_prompt()
        )
        
        # 创建 AgentExecutor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
```

#### 2.2 工具系统优化

**当前问题**: 自定义工具接口，缺乏标准化
**LangChain 解决方案**: 使用 `BaseTool` 和 `Tool` 装饰器

```python
from langchain.tools import BaseTool
from typing import Optional
from pydantic import BaseModel, Field

class K8sClusterInfoInput(BaseModel):
    """获取集群信息的输入参数"""
    namespace: Optional[str] = Field(default="default", description="命名空间")

class K8sClusterInfoTool(BaseTool):
    name = "k8s_cluster_info"
    description = "获取Kubernetes集群的基本信息，包括版本、节点状态、命名空间等"
    args_schema = K8sClusterInfoInput
    
    def _run(self, namespace: str = "default") -> str:
        # 调用现有的工具实现
        result = self._execute_k8s_tool("k8s_cluster_info", {"namespace": namespace})
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    async def _arun(self, namespace: str = "default") -> str:
        # 异步实现
        result = await self._execute_k8s_tool_async("k8s_cluster_info", {"namespace": namespace})
        return json.dumps(result, ensure_ascii=False, indent=2)
```

#### 2.3 记忆系统增强

**当前问题**: 简单的会话管理，缺乏长期记忆
**LangChain 解决方案**: 使用 `ConversationBufferWindowMemory` + `VectorStore`

```python
from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryMemory
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

class K8sDiagnosisMemory:
    def __init__(self, config: Config):
        # 短期记忆 - 最近对话
        self.short_term_memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True,
            memory_key="chat_history"
        )
        
        # 长期记忆 - 向量存储
        self.embeddings = OpenAIEmbeddings(api_key=config.llm.openai_api_key)
        self.vectorstore = Chroma(
            embedding_function=self.embeddings,
            collection_name="k8s_diagnosis_history"
        )
        
        # 总结记忆 - 对话摘要
        self.summary_memory = ConversationSummaryMemory(
            llm=self._create_langchain_llm(),
            return_messages=True
        )
    
    def add_interaction(self, user_input: str, agent_output: str, context: dict):
        """添加交互到记忆系统"""
        # 添加到短期记忆
        self.short_term_memory.save_context(
            {"input": user_input},
            {"output": agent_output}
        )
        
        # 添加到向量存储
        self.vectorstore.add_texts(
            texts=[f"User: {user_input}\nAgent: {agent_output}"],
            metadatas=[context]
        )
        
        # 更新总结记忆
        self.summary_memory.save_context(
            {"input": user_input},
            {"output": agent_output}
        )
    
    def get_relevant_history(self, query: str, k: int = 5) -> List[str]:
        """获取相关的历史记录"""
        docs = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
```

#### 2.4 链式调用优化

**当前问题**: 线性的任务执行，缺乏灵活性
**LangChain 解决方案**: 使用 `LCEL` (LangChain Expression Language)

```python
from langchain.schema import BaseOutputParser
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema.runnable import RunnablePassthrough

class DiagnosisChain:
    def __init__(self, config: Config):
        self.llm = self._create_langchain_llm()
        
        # 创建诊断链
        self.diagnosis_chain = (
            {"user_input": RunnablePassthrough()}
            | self._create_analysis_prompt()
            | self.llm
            | self._create_plan_prompt()
            | self.llm
            | self._create_execution_chain()
        )
    
    def _create_analysis_prompt(self):
        return PromptTemplate(
            input_variables=["user_input"],
            template="""
            分析以下Kubernetes问题，识别关键信息：
            
            用户问题: {user_input}
            
            请提取：
            1. 问题类型（Pod、Service、Node等）
            2. 错误症状
            3. 需要收集的信息类型
            
            分析结果：
            """
        )
    
    def _create_plan_prompt(self):
        return PromptTemplate(
            input_variables=["analysis", "available_tools"],
            template="""
            基于分析结果制定诊断计划：
            
            分析: {analysis}
            可用工具: {available_tools}
            
            请制定详细的诊断步骤：
            """
        )
    
    def _create_execution_chain(self):
        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["plan"],
                template="执行诊断计划: {plan}"
            )
        )
```

#### 2.5 提示词管理优化

**当前问题**: 硬编码的提示词，难以维护
**LangChain 解决方案**: 使用 `PromptTemplate` 和 `FewShotPromptTemplate`

```python
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector

class K8sPromptManager:
    def __init__(self, config: Config):
        self.config = config
        self.embeddings = OpenAIEmbeddings(api_key=config.llm.openai_api_key)
        
        # 创建示例选择器
        self.example_selector = SemanticSimilarityExampleSelector.from_examples(
            examples=self._get_diagnosis_examples(),
            embeddings=self.embeddings,
            vectorstore_cls=Chroma,
            k=3
        )
        
        # 创建诊断提示词模板
        self.diagnosis_prompt = FewShotPromptTemplate(
            example_selector=self.example_selector,
            example_prompt=PromptTemplate(
                input_variables=["problem", "solution"],
                template="问题: {problem}\n解决方案: {solution}"
            ),
            prefix="你是一个Kubernetes诊断专家。以下是类似的诊断案例：",
            suffix="现在请诊断以下问题：\n问题: {user_input}\n诊断步骤：",
            input_variables=["user_input"]
        )
    
    def _get_diagnosis_examples(self):
        return [
            {
                "problem": "Pod一直重启",
                "solution": "1. 检查Pod状态和事件\n2. 查看Pod日志\n3. 检查资源限制\n4. 验证镜像和配置"
            },
            {
                "problem": "Service无法访问",
                "solution": "1. 检查Service配置\n2. 验证Endpoint\n3. 测试网络连通性\n4. 检查防火墙规则"
            }
        ]
```

### 3. 迁移策略

#### 3.1 渐进式迁移

1. **第一阶段**: 保留现有接口，添加 LangChain 包装器
2. **第二阶段**: 逐步迁移核心功能到 LangChain
3. **第三阶段**: 完全使用 LangChain 架构

#### 3.2 兼容性保证

```python
# 兼容性包装器
class LangChainAgentWrapper:
    def __init__(self, config: Config):
        self.langchain_agent = K8sDiagnosisAgent(config)
        self.legacy_agent = Agent(config)  # 保留原有实现
    
    async def process_message(self, message: str, session_id: str = None):
        try:
            # 优先使用 LangChain 实现
            return await self.langchain_agent.process_message(message, session_id)
        except Exception as e:
            # 降级到原有实现
            logger.warning(f"LangChain Agent 失败，使用原有实现: {e}")
            return await self.legacy_agent.process_message(message, session_id)
```

### 4. 性能优化

#### 4.1 并行执行

```python
from langchain.agents import AgentExecutor
from concurrent.futures import ThreadPoolExecutor

class ParallelK8sAgent(AgentExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def execute_tools_parallel(self, tools_to_execute):
        """并行执行多个工具"""
        loop = asyncio.get_event_loop()
        tasks = []
        
        for tool in tools_to_execute:
            task = loop.run_in_executor(
                self.executor,
                tool._run,
                *tool.args
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

#### 4.2 缓存优化

```python
from langchain.cache import InMemoryCache, RedisCache
import redis

class CachedK8sAgent:
    def __init__(self, config: Config):
        # 使用 Redis 缓存
        redis_client = redis.Redis(
            host=config.cache.redis_host,
            port=config.cache.redis_port,
            db=config.cache.redis_db
        )
        
        self.cache = RedisCache(redis_client)
        self.agent = K8sDiagnosisAgent(config)
        
        # 启用缓存
        self.agent.llm.cache = self.cache
```

### 5. 监控和可观测性

#### 5.1 LangSmith 集成

```python
from langsmith import Client
import os

# 设置 LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"
os.environ["LANGCHAIN_PROJECT"] = "k8s-diagnosis-agent"

class MonitoredK8sAgent:
    def __init__(self, config: Config):
        self.agent = K8sDiagnosisAgent(config)
        self.client = Client()
    
    async def process_message(self, message: str, session_id: str = None):
        # 自动记录到 LangSmith
        with self.client.trace("k8s_diagnosis") as tracer:
            result = await self.agent.process_message(message, session_id)
            tracer.add_metadata({
                "session_id": session_id,
                "message_length": len(message)
            })
            return result
```

### 6. 部署和配置

#### 6.1 依赖管理

```python
# requirements.txt 新增
langchain>=0.1.0
langchain-openai>=0.1.0
langchain-community>=0.1.0
langsmith>=0.1.0
chromadb>=0.4.0
redis>=4.5.0
```

#### 6.2 配置更新

```python
# config.py 新增 LangChain 配置
class LangChainConfig(BaseSettings):
    """LangChain 配置"""
    
    # 缓存配置
    cache_enabled: bool = Field(default=True, env="LANGCHAIN_CACHE_ENABLED")
    cache_type: str = Field(default="redis", env="LANGCHAIN_CACHE_TYPE")
    
    # 监控配置
    langsmith_enabled: bool = Field(default=False, env="LANGSMITH_ENABLED")
    langsmith_api_key: Optional[str] = Field(default=None, env="LANGSMITH_API_KEY")
    
    # 向量存储配置
    vectorstore_type: str = Field(default="chroma", env="VECTORSTORE_TYPE")
    vectorstore_path: str = Field(default="./vectorstore", env="VECTORSTORE_PATH")
```

## 总结

通过 LangChain 优化，我们可以获得：

1. **标准化**: 使用业界标准的 Agent 框架
2. **可扩展性**: 更容易添加新功能和工具
3. **性能**: 更好的缓存和并行处理
4. **可观测性**: 完整的监控和调试能力
5. **维护性**: 更清晰的代码结构和文档

这个优化方案保持了向后兼容性，同时显著提升了系统的能力和可维护性。 