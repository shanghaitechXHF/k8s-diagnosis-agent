"""
系统诊断工具集合
"""
import asyncio
import subprocess
import platform
import psutil
import socket
from typing import Dict, Any, Optional
from .base import BaseTool, ToolResult, ToolStatus


class SystemInfoTool(BaseTool):
    """系统信息工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "获取系统基本信息"
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取系统信息"""
        try:
            system_info = {
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "percent": psutil.cpu_percent(interval=1),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
                },
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                    "used": psutil.virtual_memory().used,
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "used": psutil.disk_usage('/').used,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent,
                },
                "network": {
                    "hostname": socket.gethostname(),
                    "fqdn": socket.getfqdn(),
                }
            }
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=system_info,
                message="成功获取系统信息"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="获取系统信息失败"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "获取系统基本信息",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


class NetworkDiagnosticTool(BaseTool):
    """网络诊断工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "网络连通性诊断"
    
    async def execute(self, **kwargs) -> ToolResult:
        """网络诊断"""
        try:
            host = kwargs.get('host', 'google.com')
            port = kwargs.get('port', 80)
            timeout = kwargs.get('timeout', 5)
            
            # 简单的网络连通性测试
            result = await asyncio.to_thread(self._test_connection, host, port, timeout)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result,
                message="网络诊断完成"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="网络诊断失败"
            )
    
    def _test_connection(self, host: str, port: int, timeout: int) -> Dict[str, Any]:
        """测试网络连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {
                "host": host,
                "port": port,
                "connected": result == 0,
                "message": "连接成功" if result == 0 else f"连接失败: {result}"
            }
        except Exception as e:
            return {
                "host": host,
                "port": port,
                "connected": False,
                "error": str(e)
            }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "test_network",
                "description": "测试网络连通性",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "default": "google.com"},
                        "port": {"type": "integer", "default": 80},
                        "timeout": {"type": "integer", "default": 5}
                    },
                    "required": []
                }
            }
        }


class FileSystemTool(BaseTool):
    """文件系统工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "文件系统诊断"
    
    async def execute(self, **kwargs) -> ToolResult:
        """文件系统诊断"""
        try:
            path = kwargs.get('path', '/')
            
            # 获取磁盘使用情况
            disk_usage = psutil.disk_usage(path)
            
            # 获取挂载点信息
            partitions = psutil.disk_partitions()
            
            fs_info = {
                "path": path,
                "usage": {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": disk_usage.percent
                },
                "partitions": [
                    {
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "opts": p.opts
                    } for p in partitions
                ]
            }
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=fs_info,
                message="文件系统诊断完成"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="文件系统诊断失败"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "diagnose_filesystem",
                "description": "诊断文件系统",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "/"}
                    },
                    "required": []
                }
            }
        }


class ProcessTool(BaseTool):
    """进程诊断工具"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.description = "进程诊断"
    
    async def execute(self, **kwargs) -> ToolResult:
        """进程诊断"""
        try:
            process_name = kwargs.get('process_name')
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    if not process_name or process_name in proc.info['name']:
                        processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"processes": processes},
                message="进程诊断完成"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="进程诊断失败"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "diagnose_processes",
                "description": "诊断系统进程",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "process_name": {"type": "string", "description": "进程名称过滤"}
                    },
                    "required": []
                }
            }
        } 