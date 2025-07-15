"""
LangChain 记忆系统
实现多层次记忆管理，包括短期记忆、长期记忆和向量存储
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

# 注意：这些导入在实际环境中需要安装相应的包
# 这里使用 try-except 来处理可能的导入错误
try:
    from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryMemory
    from langchain.vectorstores import Chroma
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # 如果 LangChain 不可用，创建模拟类
    class ConversationBufferWindowMemory:
        def __init__(self, k=10, return_messages=True, memory_key="chat_history"):
            self.k = k
            self.return_messages = return_messages
            self.memory_key = memory_key
            self.chat_memory = MockChatMemory()
        
        def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]):
            pass
        
        def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            return {self.memory_key: []}
    
    class ConversationSummaryMemory:
        def __init__(self, llm=None, return_messages=True):
            self.llm = llm
            self.return_messages = return_messages
            self.chat_memory = MockChatMemory()
        
        def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]):
            pass
        
        def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            return {"chat_history": []}
    
    class Chroma:
        def __init__(self, embedding_function=None, collection_name="default"):
            self.embedding_function = embedding_function
            self.collection_name = collection_name
        
        def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
            pass
        
        def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
            return []
    
    class OpenAIEmbeddings:
        def __init__(self, api_key: str = None):
            self.api_key = api_key
    
    class BaseMessage:
        def __init__(self, content: str, type: str = "human"):
            self.content = content
            self.type = type
    
    class HumanMessage(BaseMessage):
        def __init__(self, content: str):
            super().__init__(content, "human")
    
    class AIMessage(BaseMessage):
        def __init__(self, content: str):
            super().__init__(content, "ai")
    
    class MockChatMemory:
        def __init__(self):
            self.messages = []
        
        def add_message(self, message):
            self.messages.append(message)
        
        def clear(self):
            self.messages.clear()
    
    LANGCHAIN_AVAILABLE = False

from ..config import Config


class K8sDiagnosisMemory:
    """K8s 诊断记忆系统"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # 短期记忆 - 最近对话
        self.short_term_memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True,
            memory_key="chat_history"
        )
        
        # 长期记忆 - 向量存储
        if LANGCHAIN_AVAILABLE and config.llm.openai_api_key:
            try:
                self.embeddings = OpenAIEmbeddings(api_key=config.llm.openai_api_key)
                self.vectorstore = Chroma(
                    embedding_function=self.embeddings,
                    collection_name="k8s_diagnosis_history"
                )
                self.vectorstore_available = True
            except Exception as e:
                print(f"警告: 无法初始化向量存储: {e}")
                self.vectorstore_available = False
                self.vectorstore = None
        else:
            self.vectorstore_available = False
            self.vectorstore = None
        
        # 总结记忆 - 对话摘要
        if LANGCHAIN_AVAILABLE:
            try:
                # 创建简单的 LLM 实例用于总结
                self.summary_llm = self._create_simple_llm()
                self.summary_memory = ConversationSummaryMemory(
                    llm=self.summary_llm,
                    return_messages=True
                )
                self.summary_memory_available = True
            except Exception as e:
                print(f"警告: 无法初始化总结记忆: {e}")
                self.summary_memory_available = False
                self.summary_memory = None
        else:
            self.summary_memory_available = False
            self.summary_memory = None
    
    def _create_simple_llm(self):
        """创建简单的 LLM 实例用于总结"""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=self.config.llm.openai_api_key,
                model="gpt-3.5-turbo",
                temperature=0.1
            )
        except ImportError:
            return None
    
    def add_interaction(self, user_input: str, agent_output: str, context: Dict[str, Any]):
        """添加交互到记忆系统"""
        try:
            # 添加到短期记忆
            self.short_term_memory.save_context(
                {"input": user_input},
                {"output": agent_output}
            )
            
            # 添加到向量存储
            if self.vectorstore_available and self.vectorstore:
                try:
                    self.vectorstore.add_texts(
                        texts=[f"User: {user_input}\nAgent: {agent_output}"],
                        metadatas=[{
                            **context,
                            "timestamp": datetime.now().isoformat(),
                            "interaction_type": "k8s_diagnosis"
                        }]
                    )
                except Exception as e:
                    print(f"警告: 添加向量存储失败: {e}")
            
            # 更新总结记忆
            if self.summary_memory_available and self.summary_memory:
                try:
                    self.summary_memory.save_context(
                        {"input": user_input},
                        {"output": agent_output}
                    )
                except Exception as e:
                    print(f"警告: 更新总结记忆失败: {e}")
                    
        except Exception as e:
            print(f"警告: 添加交互到记忆系统失败: {e}")
    
    def get_relevant_history(self, query: str, k: int = 5) -> List[str]:
        """获取相关的历史记录"""
        if not self.vectorstore_available or not self.vectorstore:
            return []
        
        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            return [doc.page_content for doc in docs]
        except Exception as e:
            print(f"警告: 获取相关历史记录失败: {e}")
            return []
    
    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        if not self.summary_memory_available or not self.summary_memory:
            return "记忆系统不可用"
        
        try:
            variables = self.summary_memory.load_memory_variables({})
            return variables.get("chat_history", "无摘要")
        except Exception as e:
            print(f"警告: 获取对话摘要失败: {e}")
            return "获取摘要失败"
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的消息"""
        try:
            messages = self.short_term_memory.chat_memory.messages
            recent_messages = messages[-limit:] if len(messages) > limit else messages
            
            return [
                {
                    "type": msg.type,
                    "content": msg.content,
                    "timestamp": datetime.now().isoformat()  # 简化处理
                }
                for msg in recent_messages
            ]
        except Exception as e:
            print(f"警告: 获取最近消息失败: {e}")
            return []
    
    def clear_memory(self):
        """清除所有记忆"""
        try:
            # 清除短期记忆
            self.short_term_memory.chat_memory.clear()
            
            # 清除总结记忆
            if self.summary_memory_available and self.summary_memory:
                self.summary_memory.chat_memory.clear()
            
            print("记忆已清除")
        except Exception as e:
            print(f"警告: 清除记忆失败: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        try:
            short_term_count = len(self.short_term_memory.chat_memory.messages)
            
            stats = {
                "short_term_messages": short_term_count,
                "vectorstore_available": self.vectorstore_available,
                "summary_memory_available": self.summary_memory_available,
                "langchain_available": LANGCHAIN_AVAILABLE
            }
            
            if self.summary_memory_available:
                try:
                    summary = self.get_conversation_summary()
                    stats["has_summary"] = bool(summary and summary != "无摘要")
                except:
                    stats["has_summary"] = False
            
            return stats
        except Exception as e:
            return {
                "error": str(e),
                "langchain_available": LANGCHAIN_AVAILABLE
            } 