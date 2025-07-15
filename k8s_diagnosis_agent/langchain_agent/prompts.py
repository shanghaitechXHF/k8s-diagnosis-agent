"""
LangChain 提示词管理
实现动态提示词生成和管理
"""
from typing import Dict, Any, List, Optional
import json

# 注意：这些导入在实际环境中需要安装相应的包
# 这里使用 try-except 来处理可能的导入错误
try:
    from langchain.prompts import PromptTemplate, FewShotPromptTemplate
    from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # 如果 LangChain 不可用，创建模拟类
    class PromptTemplate:
        def __init__(self, input_variables: List[str], template: str):
            self.input_variables = input_variables
            self.template = template
        
        def format(self, **kwargs) -> str:
            return self.template.format(**kwargs)
    
    class FewShotPromptTemplate:
        def __init__(self, examples: List[Dict[str, str]], example_prompt: PromptTemplate, 
                     prefix: str, suffix: str, input_variables: List[str]):
            self.examples = examples
            self.example_prompt = example_prompt
            self.prefix = prefix
            self.suffix = suffix
            self.input_variables = input_variables
        
        def format(self, **kwargs) -> str:
            return f"{self.prefix}\n{self.suffix}"
    
    class SemanticSimilarityExampleSelector:
        def __init__(self, examples: List[Dict[str, str]], embeddings, vectorstore_cls):
            self.examples = examples
        
        def select_examples(self, input_variables: Dict[str, Any]) -> List[Dict[str, str]]:
            return self.examples[:2]  # 返回前两个示例
    
    class OpenAIEmbeddings:
        def __init__(self, api_key: str = None):
            self.api_key = api_key
    
    class Chroma:
        def __init__(self, embedding_function=None, collection_name="default"):
            self.embedding_function = embedding_function
            self.collection_name = collection_name
    
    LANGCHAIN_AVAILABLE = False

from ..config import Config


class K8sPromptManager:
    """K8s 提示词管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.embeddings = self._create_embeddings()
        self.examples = self._load_examples()
        self.example_selector = self._create_example_selector()
    
    def _create_embeddings(self):
        """创建嵌入模型"""
        if not LANGCHAIN_AVAILABLE or not self.config.llm.openai_api_key:
            return None
        
        try:
            return OpenAIEmbeddings(api_key=self.config.llm.openai_api_key)
        except Exception as e:
            print(f"警告: 无法创建嵌入模型: {e}")
            return None
    
    def _load_examples(self) -> List[Dict[str, str]]:
        """加载示例"""
        return [
            {
                "question": "Pod一直处于Pending状态怎么办？",
                "answer": "首先检查节点资源是否充足，然后查看Pod的事件信息，最后检查调度器日志。",
                "tools": "k8s_pod_info, k8s_events, k8s_node_info"
            },
            {
                "question": "Service无法访问Pod怎么办？",
                "answer": "检查Service的标签选择器是否匹配Pod标签，验证端口配置，查看端点状态。",
                "tools": "k8s_pod_info, k8s_cluster_info"
            },
            {
                "question": "节点资源不足怎么办？",
                "answer": "查看节点资源使用情况，检查是否有资源请求过高，考虑扩容或迁移Pod。",
                "tools": "k8s_node_info, k8s_pod_info"
            },
            {
                "question": "Pod频繁重启怎么办？",
                "answer": "查看Pod日志和事件，检查健康检查配置，分析资源使用情况。",
                "tools": "k8s_logs, k8s_events, k8s_pod_info"
            },
            {
                "question": "集群连接失败怎么办？",
                "answer": "检查API服务器状态，验证认证配置，查看集群事件和节点状态。",
                "tools": "k8s_cluster_info, k8s_events, k8s_node_info"
            }
        ]
    
    def _create_example_selector(self):
        """创建示例选择器"""
        if not LANGCHAIN_AVAILABLE or not self.embeddings:
            return None
        
        try:
            return SemanticSimilarityExampleSelector(
                examples=self.examples,
                embeddings=self.embeddings,
                vectorstore_cls=Chroma
            )
        except Exception as e:
            print(f"警告: 无法创建示例选择器: {e}")
            return None
    
    def create_system_prompt(self) -> str:
        """创建系统提示词"""
        return """你是一个专业的Kubernetes诊断专家，具有丰富的容器编排和故障排查经验。

你的主要职责：
1. 分析用户描述的Kubernetes问题
2. 制定系统性的诊断计划
3. 使用合适的工具收集信息
4. 分析收集到的数据
5. 提供准确的诊断结果和解决方案

可用工具：
- k8s_cluster_info: 获取集群基本信息
- k8s_pod_info: 获取Pod详细信息
- k8s_node_info: 获取节点信息
- k8s_events: 获取集群事件
- k8s_logs: 获取Pod日志
- system_info: 获取系统信息

诊断原则：
1. 系统性：按照逻辑顺序进行诊断
2. 全面性：收集足够的信息进行分析
3. 准确性：基于事实数据做出判断
4. 实用性：提供可操作的解决方案

请始终保持专业、耐心和准确。"""
    
    def create_diagnosis_prompt(self, user_question: str, chat_history: List[Dict[str, str]] = None) -> str:
        """创建诊断提示词"""
        # 基础提示词
        base_prompt = self.create_system_prompt()
        
        # 添加聊天历史
        history_text = ""
        if chat_history:
            history_text = "\n\n对话历史：\n"
            for msg in chat_history[-5:]:  # 只保留最近5条
                role = "用户" if msg.get("type") == "human" else "助手"
                history_text += f"{role}: {msg.get('content', '')}\n"
        
        # 添加相关示例
        examples_text = ""
        if self.example_selector:
            try:
                selected_examples = self.example_selector.select_examples({"question": user_question})
                if selected_examples:
                    examples_text = "\n\n相关示例：\n"
                    for example in selected_examples:
                        examples_text += f"问题: {example['question']}\n"
                        examples_text += f"答案: {example['answer']}\n"
                        examples_text += f"工具: {example['tools']}\n\n"
            except Exception as e:
                print(f"警告: 选择示例失败: {e}")
        
        # 组合完整提示词
        full_prompt = f"""{base_prompt}{history_text}{examples_text}

当前问题: {user_question}

请按照以下步骤进行诊断：
1. 分析问题类型和关键信息
2. 制定诊断计划
3. 使用合适的工具收集信息
4. 分析收集到的数据
5. 提供诊断结果和解决方案

请开始诊断："""
        
        return full_prompt
    
    def create_analysis_prompt(self, data: Dict[str, Any], context: str = "") -> str:
        """创建分析提示词"""
        return f"""请分析以下Kubernetes数据：

数据: {json.dumps(data, ensure_ascii=False, indent=2)}
上下文: {context}

请从以下角度进行分析：
1. 数据完整性：数据是否完整，是否缺少关键信息
2. 状态评估：各项指标是否正常，是否有异常状态
3. 问题识别：发现的具体问题和异常
4. 原因分析：可能的原因和影响因素
5. 影响评估：问题对系统的影响程度
6. 解决建议：具体的解决步骤和建议

分析结果："""
    
    def create_summary_prompt(self, diagnosis_results: List[Dict[str, Any]], user_question: str) -> str:
        """创建总结提示词"""
        # 格式化诊断结果
        results_text = ""
        for i, result in enumerate(diagnosis_results, 1):
            tool_name = result.get('tool_name', 'Unknown')
            status = result.get('result', {}).get('status', 'unknown')
            message = result.get('result', {}).get('message', '')
            results_text += f"{i}. {tool_name} ({status}): {message}\n"
        
        return f"""基于以下诊断结果生成总结报告：

用户问题: {user_question}

诊断结果:
{results_text}

请生成包含以下内容的总结报告：
1. 诊断概述：简要描述诊断过程和主要发现
2. 问题总结：列出发现的主要问题
3. 系统状态：评估整体系统状态
4. 解决方案：提供具体的解决步骤
5. 预防建议：如何避免类似问题
6. 总结：关键要点和建议

总结报告："""
    
    def create_tool_selection_prompt(self, user_question: str, available_tools: List[str]) -> str:
        """创建工具选择提示词"""
        tools_text = "\n".join([f"- {tool}" for tool in available_tools])
        
        return f"""基于用户问题选择合适的诊断工具：

用户问题: {user_question}

可用工具:
{tools_text}

请选择最合适的工具来诊断这个问题。考虑：
1. 问题类型（Pod、Service、Node等）
2. 需要收集的信息类型
3. 工具的功能和适用场景

选择的工具和理由："""
    
    def create_follow_up_prompt(self, previous_results: List[Dict[str, Any]], user_question: str) -> str:
        """创建后续问题提示词"""
        results_summary = ""
        for result in previous_results:
            tool_name = result.get('tool_name', 'Unknown')
            status = result.get('result', {}).get('status', 'unknown')
            results_summary += f"- {tool_name}: {status}\n"
        
        return f"""基于之前的诊断结果，继续分析：

用户问题: {user_question}

之前的诊断结果:
{results_summary}

请分析：
1. 之前的诊断是否解决了问题
2. 还需要收集哪些额外信息
3. 下一步应该采取什么行动
4. 是否需要使用其他工具

分析结果："""
    
    def create_error_handling_prompt(self, error: str, context: str = "") -> str:
        """创建错误处理提示词"""
        return f"""遇到错误，请分析并提供解决方案：

错误信息: {error}
上下文: {context}

请分析：
1. 错误类型和原因
2. 对诊断过程的影响
3. 可能的解决方案
4. 替代方案或绕过方法

分析结果："""
    
    def get_prompt_template(self, template_name: str) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        templates = {
            "system": PromptTemplate(
                input_variables=[],
                template=self.create_system_prompt()
            ),
            "diagnosis": PromptTemplate(
                input_variables=["user_question", "chat_history"],
                template="{system_prompt}\n\n当前问题: {user_question}\n\n请开始诊断："
            ),
            "analysis": PromptTemplate(
                input_variables=["data", "context"],
                template=self.create_analysis_prompt({}, "")
            ),
            "summary": PromptTemplate(
                input_variables=["diagnosis_results", "user_question"],
                template=self.create_summary_prompt([], "")
            )
        }
        
        return templates.get(template_name)
    
    def format_prompt(self, template_name: str, **kwargs) -> str:
        """格式化提示词"""
        template = self.get_prompt_template(template_name)
        if template:
            return template.format(**kwargs)
        else:
            return f"未知模板: {template_name}"
    
    def get_agent_prompt(self):
        """获取 Agent 提示词模板"""
        if not LANGCHAIN_AVAILABLE:
            # 返回简单的字符串提示词
            return self.create_system_prompt()
        
        try:
            from langchain.prompts import PromptTemplate
            
            # 创建 Agent 提示词模板
            template = PromptTemplate(
                input_variables=["input", "chat_history", "agent_scratchpad"],
                template="""你是一个专业的Kubernetes诊断专家。

{system_prompt}

可用工具：
{tools}

对话历史：
{chat_history}

当前问题: {input}

{agent_scratchpad}

请使用合适的工具来诊断问题。"""
            )
            return template
        except ImportError:
            # 如果 LangChain 不可用，返回字符串
            return self.create_system_prompt() 