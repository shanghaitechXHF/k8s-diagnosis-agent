# Model Context Protocol (MCP) 接入指南

## 概述

K8s诊断Agent通过Model Context Protocol (MCP) 支持扩展外部工具和服务。MCP是一个开放的协议，允许AI应用程序与外部工具和数据源进行安全的交互。

## MCP协议简介

MCP (Model Context Protocol) 是一个标准化的协议，用于AI应用程序与外部工具、数据源和服务的集成。它提供了：

- 标准化的工具和资源接口
- 安全的通信机制
- 灵活的扩展能力
- 跨平台兼容性

## 支持的MCP功能

### 1. 工具扩展
- SSH连接管理
- 远程命令执行
- 文件传输
- 网络诊断
- 数据库连接
- 监控系统集成

### 2. 资源访问
- 外部配置文件
- 日志文件
- 监控数据
- 文档和知识库

### 3. 服务集成
- 通知系统
- 票据系统
- 聊天机器人
- 报告生成

## 快速开始

### 1. 安装MCP客户端

```bash
# 使用pip安装
pip install model-context-protocol

# 或者从源码安装
git clone https://github.com/modelcontextprotocol/python-sdk.git
cd python-sdk
pip install -e .
```

### 2. 配置MCP服务器

创建MCP服务器配置文件 `mcp-config.json`：

```json
{
  "mcpServers": {
    "ssh-tools": {
      "command": "python",
      "args": ["-m", "mcp_ssh_tools"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    },
    "monitoring": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-prometheus"],
      "env": {
        "PROMETHEUS_URL": "http://localhost:9090"
      }
    }
  }
}
```

### 3. 在Agent中配置MCP

更新 `config.py` 中的MCP配置：

```python
@dataclass
class MCPConfig:
    """MCP配置"""
    enabled: bool = True
    config_file: str = "mcp-config.json"
    server_timeout: int = 30
    max_retries: int = 3
    servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
```

## MCP工具开发

### 1. 创建SSH工具MCP服务器

```python
#!/usr/bin/env python3
"""
SSH工具MCP服务器
"""
import asyncio
import json
import sys
from typing import Dict, Any, List, Optional

from mcp.server import Server
from mcp.server.models import Tool, TextContent, EmbeddedResource
from mcp.server.session import ServerSession
from mcp.types import TextResourceContents, ImageResourceContents, EmbeddedResourceContents

import paramiko
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SSHToolsServer:
    """SSH工具MCP服务器"""
    
    def __init__(self):
        self.server = Server("ssh-tools")
        self.connections: Dict[str, paramiko.SSHClient] = {}
        self.setup_tools()
    
    def setup_tools(self):
        """设置工具"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="ssh_connect",
                    description="连接到SSH服务器",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "host": {"type": "string", "description": "SSH主机地址"},
                            "port": {"type": "integer", "description": "SSH端口", "default": 22},
                            "username": {"type": "string", "description": "用户名"},
                            "password": {"type": "string", "description": "密码"},
                            "key_filename": {"type": "string", "description": "私钥文件路径"}
                        },
                        "required": ["host", "username"]
                    }
                ),
                Tool(
                    name="ssh_execute",
                    description="执行SSH命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "连接ID"},
                            "command": {"type": "string", "description": "要执行的命令"},
                            "timeout": {"type": "integer", "description": "超时时间", "default": 30}
                        },
                        "required": ["connection_id", "command"]
                    }
                ),
                Tool(
                    name="ssh_disconnect",
                    description="断开SSH连接",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "连接ID"}
                        },
                        "required": ["connection_id"]
                    }
                ),
                Tool(
                    name="ssh_file_transfer",
                    description="SSH文件传输",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connection_id": {"type": "string", "description": "连接ID"},
                            "local_path": {"type": "string", "description": "本地文件路径"},
                            "remote_path": {"type": "string", "description": "远程文件路径"},
                            "direction": {"type": "string", "enum": ["upload", "download"], "description": "传输方向"}
                        },
                        "required": ["connection_id", "local_path", "remote_path", "direction"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具"""
            if name == "ssh_connect":
                return await self.ssh_connect(arguments)
            elif name == "ssh_execute":
                return await self.ssh_execute(arguments)
            elif name == "ssh_disconnect":
                return await self.ssh_disconnect(arguments)
            elif name == "ssh_file_transfer":
                return await self.ssh_file_transfer(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def ssh_connect(self, args: Dict[str, Any]) -> List[TextContent]:
        """SSH连接"""
        try:
            host = args["host"]
            port = args.get("port", 22)
            username = args["username"]
            password = args.get("password")
            key_filename = args.get("key_filename")
            
            # 创建SSH客户端
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 连接
            if key_filename:
                client.connect(host, port, username, key_filename=key_filename)
            else:
                client.connect(host, port, username, password)
            
            # 生成连接ID
            connection_id = f"{username}@{host}:{port}"
            self.connections[connection_id] = client
            
            return [
                TextContent(
                    type="text",
                    text=f"成功连接到 {connection_id}"
                )
            ]
            
        except Exception as e:
            logger.error(f"SSH连接失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"SSH连接失败: {str(e)}"
                )
            ]
    
    async def ssh_execute(self, args: Dict[str, Any]) -> List[TextContent]:
        """执行SSH命令"""
        try:
            connection_id = args["connection_id"]
            command = args["command"]
            timeout = args.get("timeout", 30)
            
            if connection_id not in self.connections:
                return [
                    TextContent(
                        type="text",
                        text=f"连接 {connection_id} 不存在"
                    )
                ]
            
            client = self.connections[connection_id]
            
            # 执行命令
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            
            # 获取输出
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            result = {
                "command": command,
                "output": output,
                "error": error,
                "exit_code": stdout.channel.recv_exit_status()
            }
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False)
                )
            ]
            
        except Exception as e:
            logger.error(f"SSH命令执行失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"SSH命令执行失败: {str(e)}"
                )
            ]
    
    async def ssh_disconnect(self, args: Dict[str, Any]) -> List[TextContent]:
        """断开SSH连接"""
        try:
            connection_id = args["connection_id"]
            
            if connection_id in self.connections:
                client = self.connections[connection_id]
                client.close()
                del self.connections[connection_id]
                
                return [
                    TextContent(
                        type="text",
                        text=f"已断开连接 {connection_id}"
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"连接 {connection_id} 不存在"
                    )
                ]
                
        except Exception as e:
            logger.error(f"SSH断开连接失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"SSH断开连接失败: {str(e)}"
                )
            ]
    
    async def ssh_file_transfer(self, args: Dict[str, Any]) -> List[TextContent]:
        """SSH文件传输"""
        try:
            connection_id = args["connection_id"]
            local_path = args["local_path"]
            remote_path = args["remote_path"]
            direction = args["direction"]
            
            if connection_id not in self.connections:
                return [
                    TextContent(
                        type="text",
                        text=f"连接 {connection_id} 不存在"
                    )
                ]
            
            client = self.connections[connection_id]
            sftp = client.open_sftp()
            
            if direction == "upload":
                sftp.put(local_path, remote_path)
                message = f"文件已上传: {local_path} -> {remote_path}"
            else:  # download
                sftp.get(remote_path, local_path)
                message = f"文件已下载: {remote_path} -> {local_path}"
            
            sftp.close()
            
            return [
                TextContent(
                    type="text",
                    text=message
                )
            ]
            
        except Exception as e:
            logger.error(f"SSH文件传输失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"SSH文件传输失败: {str(e)}"
                )
            ]
    
    async def run(self):
        """运行服务器"""
        async with self.server.session() as session:
            await session.run()

def main():
    """主函数"""
    server = SSHToolsServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
```

### 2. 创建监控工具MCP服务器

```python
#!/usr/bin/env python3
"""
监控工具MCP服务器
"""
import asyncio
import json
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.models import Tool, TextContent
from mcp.server.session import ServerSession

import aiohttp
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoringServer:
    """监控工具MCP服务器"""
    
    def __init__(self):
        self.server = Server("monitoring")
        self.prometheus_url = "http://localhost:9090"
        self.setup_tools()
    
    def setup_tools(self):
        """设置工具"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="prometheus_query",
                    description="查询Prometheus指标",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "PromQL查询语句"},
                            "time": {"type": "string", "description": "查询时间 (RFC3339)"},
                            "timeout": {"type": "string", "description": "查询超时时间", "default": "30s"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="prometheus_query_range",
                    description="查询Prometheus时间范围指标",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "PromQL查询语句"},
                            "start": {"type": "string", "description": "开始时间 (RFC3339)"},
                            "end": {"type": "string", "description": "结束时间 (RFC3339)"},
                            "step": {"type": "string", "description": "查询步长", "default": "15s"}
                        },
                        "required": ["query", "start", "end"]
                    }
                ),
                Tool(
                    name="get_alerts",
                    description="获取活跃告警",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filter": {"type": "string", "description": "告警过滤器"},
                            "silenced": {"type": "boolean", "description": "包含静音告警", "default": False}
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具"""
            if name == "prometheus_query":
                return await self.prometheus_query(arguments)
            elif name == "prometheus_query_range":
                return await self.prometheus_query_range(arguments)
            elif name == "get_alerts":
                return await self.get_alerts(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def prometheus_query(self, args: Dict[str, Any]) -> List[TextContent]:
        """查询Prometheus指标"""
        try:
            query = args["query"]
            time = args.get("time")
            timeout = args.get("timeout", "30s")
            
            params = {
                "query": query,
                "timeout": timeout
            }
            if time:
                params["time"] = time
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(data, indent=2, ensure_ascii=False)
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Prometheus查询失败: HTTP {response.status}"
                            )
                        ]
                        
        except Exception as e:
            logger.error(f"Prometheus查询失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"Prometheus查询失败: {str(e)}"
                )
            ]
    
    async def prometheus_query_range(self, args: Dict[str, Any]) -> List[TextContent]:
        """查询Prometheus时间范围指标"""
        try:
            query = args["query"]
            start = args["start"]
            end = args["end"]
            step = args.get("step", "15s")
            
            params = {
                "query": query,
                "start": start,
                "end": end,
                "step": step
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.prometheus_url}/api/v1/query_range",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(data, indent=2, ensure_ascii=False)
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Prometheus范围查询失败: HTTP {response.status}"
                            )
                        ]
                        
        except Exception as e:
            logger.error(f"Prometheus范围查询失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"Prometheus范围查询失败: {str(e)}"
                )
            ]
    
    async def get_alerts(self, args: Dict[str, Any]) -> List[TextContent]:
        """获取活跃告警"""
        try:
            filter_param = args.get("filter")
            silenced = args.get("silenced", False)
            
            params = {}
            if filter_param:
                params["filter"] = filter_param
            if silenced:
                params["silenced"] = "true"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.prometheus_url}/api/v1/alerts",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(data, indent=2, ensure_ascii=False)
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"获取告警失败: HTTP {response.status}"
                            )
                        ]
                        
        except Exception as e:
            logger.error(f"获取告警失败: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"获取告警失败: {str(e)}"
                )
            ]
    
    async def run(self):
        """运行服务器"""
        async with self.server.session() as session:
            await session.run()

def main():
    """主函数"""
    server = MonitoringServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
```

## 最佳实践

### 1. 安全性
- 使用加密的SSH密钥认证
- 限制MCP服务器的访问权限
- 定期轮换认证凭据
- 使用安全的通信协议

### 2. 性能优化
- 合理设置连接超时时间
- 使用连接池管理资源
- 实现异步操作
- 缓存频繁访问的数据

### 3. 错误处理
- 实现重试机制
- 提供详细的错误信息
- 记录操作日志
- 优雅地处理连接失败

### 4. 监控和日志
- 监控MCP服务器状态
- 记录所有操作日志
- 设置告警规则
- 定期检查连接状态

## 常见问题

### Q: 如何调试MCP服务器？
A: 可以通过以下方式调试：
- 增加日志级别到DEBUG
- 使用MCP Inspector工具
- 检查服务器的stdout/stderr输出
- 验证配置文件语法

### Q: 如何处理网络连接问题？
A: 建议：
- 实现自动重连机制
- 设置合理的超时时间
- 使用健康检查
- 提供降级策略

### Q: 如何扩展更多工具？
A: 可以：
- 创建新的MCP服务器
- 在现有服务器中添加新工具
- 使用MCP SDK简化开发
- 参考现有工具的实现

## 更多资源

- [MCP官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP工具示例](https://github.com/modelcontextprotocol/servers)
- [社区贡献的MCP服务器](https://github.com/modelcontextprotocol/servers/tree/main/src)

## 贡献指南

欢迎贡献更多MCP工具和服务器！请参考项目的贡献指南，提交Pull Request时请包含：

1. 工具的详细文档
2. 使用示例
3. 测试用例
4. 安全性说明

---

如有问题或建议，请在GitHub Issues中提出。 