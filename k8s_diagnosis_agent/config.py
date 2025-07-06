"""
配置管理模块
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseSettings, Field


class LLMConfig(BaseSettings):
    """大模型配置"""
    
    # OpenAI/GPT配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4-turbo", env="OPENAI_MODEL")
    
    # Claude配置
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    claude_base_url: Optional[str] = Field(default=None, env="CLAUDE_BASE_URL")
    claude_model: str = Field(default="claude-3-opus-20240229", env="CLAUDE_MODEL")
    
    # DeepSeek配置
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    deepseek_base_url: Optional[str] = Field(default="https://api.deepseek.com/v1", env="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-chat", env="DEEPSEEK_MODEL")
    
    # 默认使用的模型
    default_model: str = Field(default="gpt-4", env="DEFAULT_MODEL")
    
    # 模型参数
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS")
    timeout: int = Field(default=60, env="LLM_TIMEOUT")


class KubernetesConfig(BaseSettings):
    """Kubernetes配置"""
    
    # kubeconfig文件路径
    kubeconfig_path: Optional[str] = Field(default=None, env="KUBECONFIG_PATH")
    
    # 集群配置
    cluster_name: Optional[str] = Field(default=None, env="CLUSTER_NAME")
    namespace: str = Field(default="default", env="K8S_NAMESPACE")
    
    # 认证配置
    use_in_cluster_config: bool = Field(default=False, env="USE_IN_CLUSTER_CONFIG")
    
    # 超时配置
    api_timeout: int = Field(default=30, env="K8S_API_TIMEOUT")


class MCPConfig(BaseSettings):
    """MCP (Model Context Protocol) 配置"""
    
    # MCP服务器配置
    mcp_enabled: bool = Field(default=True, env="MCP_ENABLED")
    mcp_server_port: int = Field(default=3001, env="MCP_SERVER_PORT")
    mcp_server_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    
    # 外部工具配置
    external_tools_config: Dict[str, Any] = Field(default_factory=dict, env="EXTERNAL_TOOLS_CONFIG")


class WebConfig(BaseSettings):
    """Web服务配置"""
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="WEB_HOST")
    port: int = Field(default=8000, env="WEB_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 安全配置
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # 文件上传配置
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    upload_path: str = Field(default="uploads", env="UPLOAD_PATH")


class LoggingConfig(BaseSettings):
    """日志配置"""
    
    # 日志级别
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # 日志格式
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>",
        env="LOG_FORMAT"
    )
    
    # 日志文件
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="500 MB", env="LOG_ROTATION")
    log_retention: str = Field(default="7 days", env="LOG_RETENTION")


class Config(BaseSettings):
    """主配置类"""
    
    # 子配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    kubernetes: KubernetesConfig = Field(default_factory=KubernetesConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # 全局配置
    app_name: str = Field(default="k8s-diagnosis-agent", env="APP_NAME")
    version: str = Field(default="0.1.0", env="APP_VERSION")
    description: str = Field(default="AI Agent for Kubernetes cluster fault diagnosis", env="APP_DESCRIPTION")
    
    # 会话配置
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")  # 1小时
    max_conversation_length: int = Field(default=50, env="MAX_CONVERSATION_LENGTH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm = LLMConfig()
        self.kubernetes = KubernetesConfig()
        self.mcp = MCPConfig()
        self.web = WebConfig()
        self.logging = LoggingConfig()


# 全局配置实例
config = Config() 