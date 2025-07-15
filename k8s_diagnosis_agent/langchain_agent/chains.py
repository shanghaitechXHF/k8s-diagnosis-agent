"""
LangChain 链式调用
实现诊断链和自定义 Chain
"""
from typing import Dict, Any, List, Optional

# 注意：这些导入在实际环境中需要安装相应的包
# 这里使用 try-except 来处理可能的导入错误
try:
    from langchain.schema import BaseOutputParser
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from langchain.schema.runnable import RunnablePassthrough
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # 如果 LangChain 不可用，创建模拟类
    class BaseOutputParser:
        def parse(self, text: str) -> Any:
            return text
    
    class PromptTemplate:
        def __init__(self, input_variables: List[str], template: str):
            self.input_variables = input_variables
            self.template = template
        
        def format(self, **kwargs) -> str:
            return self.template.format(**kwargs)
    
    class LLMChain:
        def __init__(self, llm=None, prompt=None):
            self.llm = llm
            self.prompt = prompt
        
        async def ainvoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            return {"text": "LangChain not available"}
    
    class RunnablePassthrough:
        def __init__(self):
            pass
    
    LANGCHAIN_AVAILABLE = False

from ..config import Config


class DiagnosisChain:
    """诊断链 - 使用 LCEL (LangChain Expression Language)"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = self._create_langchain_llm()
        
        if LANGCHAIN_AVAILABLE and self.llm:
            # 创建诊断链
            self.diagnosis_chain = self._create_diagnosis_chain()
        else:
            self.diagnosis_chain = None
    
    def _create_langchain_llm(self):
        """创建 LangChain LLM 实例"""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=self.config.llm.openai_api_key,
                model=self.config.llm.openai_model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
        except ImportError:
            return None
    
    def _create_diagnosis_chain(self):
        """创建诊断链"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return None
        
        try:
            # 创建诊断链
            chain = (
                {"user_input": RunnablePassthrough()}
                | self._create_analysis_prompt()
                | self.llm
                | self._create_plan_prompt()
                | self.llm
                | self._create_execution_chain()
            )
            return chain
        except Exception as e:
            print(f"警告: 创建诊断链失败: {e}")
            return None
    
    def _create_analysis_prompt(self):
        """创建分析提示词"""
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
        """创建计划提示词"""
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
        """创建执行链"""
        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["plan"],
                template="执行诊断计划: {plan}"
            )
        )
    
    async def execute_diagnosis(self, user_input: str) -> Dict[str, Any]:
        """执行诊断链"""
        if not self.diagnosis_chain:
            return {
                "error": "诊断链不可用",
                "user_input": user_input,
                "result": "LangChain 不可用，无法执行诊断"
            }
        
        try:
            # 获取可用工具信息
            available_tools = self._get_available_tools_info()
            
            # 执行诊断链
            result = await self.diagnosis_chain.ainvoke({
                "user_input": user_input,
                "available_tools": available_tools
            })
            
            return {
                "user_input": user_input,
                "result": result.get("text", "执行完成"),
                "success": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "user_input": user_input,
                "result": f"执行诊断失败: {str(e)}",
                "success": False
            }
    
    def _get_available_tools_info(self) -> str:
        """获取可用工具信息"""
        tools = [
            "k8s_cluster_info - 获取集群信息",
            "k8s_pod_info - 获取Pod信息", 
            "k8s_node_info - 获取节点信息",
            "k8s_events - 获取事件信息",
            "k8s_logs - 获取日志信息",
            "system_info - 获取系统信息"
        ]
        return ", ".join(tools)


class K8sAnalysisChain:
    """K8s 分析链"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = self._create_langchain_llm()
        
        if LANGCHAIN_AVAILABLE and self.llm:
            self.analysis_chain = self._create_analysis_chain()
        else:
            self.analysis_chain = None
    
    def _create_langchain_llm(self):
        """创建 LangChain LLM 实例"""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=self.config.llm.openai_api_key,
                model=self.config.llm.openai_model,
                temperature=0.1,  # 分析时使用较低的温度
                max_tokens=self.config.llm.max_tokens
            )
        except ImportError:
            return None
    
    def _create_analysis_chain(self):
        """创建分析链"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return None
        
        try:
            analysis_prompt = PromptTemplate(
                input_variables=["data", "context"],
                template="""
                分析以下Kubernetes数据，识别问题和异常：
                
                数据: {data}
                上下文: {context}
                
                请分析：
                1. 数据是否正常
                2. 发现的问题
                3. 可能的原因
                4. 建议的解决方案
                
                分析结果：
                """
            )
            
            return LLMChain(
                llm=self.llm,
                prompt=analysis_prompt
            )
        except Exception as e:
            print(f"警告: 创建分析链失败: {e}")
            return None
    
    async def analyze_data(self, data: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """分析数据"""
        if not self.analysis_chain:
            return {
                "error": "分析链不可用",
                "data": data,
                "analysis": "LangChain 不可用，无法进行分析"
            }
        
        try:
            result = await self.analysis_chain.ainvoke({
                "data": str(data),
                "context": context
            })
            
            return {
                "data": data,
                "context": context,
                "analysis": result.get("text", "分析完成"),
                "success": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "data": data,
                "context": context,
                "analysis": f"分析失败: {str(e)}",
                "success": False
            }


class K8sSummaryChain:
    """K8s 总结链"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = self._create_langchain_llm()
        
        if LANGCHAIN_AVAILABLE and self.llm:
            self.summary_chain = self._create_summary_chain()
        else:
            self.summary_chain = None
    
    def _create_langchain_llm(self):
        """创建 LangChain LLM 实例"""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=self.config.llm.openai_api_key,
                model=self.config.llm.openai_model,
                temperature=0.1,  # 总结时使用较低的温度
                max_tokens=self.config.llm.max_tokens
            )
        except ImportError:
            return None
    
    def _create_summary_chain(self):
        """创建总结链"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return None
        
        try:
            summary_prompt = PromptTemplate(
                input_variables=["diagnosis_results", "user_question"],
                template="""
                基于以下诊断结果生成总结报告：
                
                用户问题: {user_question}
                诊断结果: {diagnosis_results}
                
                请生成包含以下内容的总结：
                1. 诊断概述
                2. 发现的问题
                3. 系统状态评估
                4. 建议的解决方案
                5. 总结
                
                总结报告：
                """
            )
            
            return LLMChain(
                llm=self.llm,
                prompt=summary_prompt
            )
        except Exception as e:
            print(f"警告: 创建总结链失败: {e}")
            return None
    
    async def generate_summary(self, diagnosis_results: List[Dict[str, Any]], user_question: str) -> Dict[str, Any]:
        """生成总结"""
        if not self.summary_chain:
            return {
                "error": "总结链不可用",
                "summary": "LangChain 不可用，无法生成总结",
                "user_question": user_question
            }
        
        try:
            # 格式化诊断结果
            results_text = "\n".join([
                f"- {result.get('tool_name', 'Unknown')}: {result.get('result', {}).get('message', '')}"
                for result in diagnosis_results
            ])
            
            result = await self.summary_chain.ainvoke({
                "diagnosis_results": results_text,
                "user_question": user_question
            })
            
            return {
                "user_question": user_question,
                "diagnosis_results": diagnosis_results,
                "summary": result.get("text", "总结生成完成"),
                "success": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "user_question": user_question,
                "diagnosis_results": diagnosis_results,
                "summary": f"生成总结失败: {str(e)}",
                "success": False
            } 