"""
基础测试
"""
import pytest
from k8s_diagnosis_agent.config import Config
from k8s_diagnosis_agent.tools import tool_registry


def test_config_creation():
    """测试配置创建"""
    config = Config()
    assert config.app_name == "k8s-diagnosis-agent"
    assert config.version == "0.1.0"


def test_tool_registry():
    """测试工具注册表"""
    tools = tool_registry.get_all_tools()
    assert len(tools) > 0
    assert "k8s_cluster_info" in tools
    assert "system_info" in tools


def test_k8s_tools():
    """测试k8s工具"""
    k8s_tools = tool_registry.get_k8s_tools()
    assert len(k8s_tools) > 0
    for tool_name in k8s_tools:
        assert tool_name.startswith("k8s_")


def test_system_tools():
    """测试系统工具"""
    system_tools = tool_registry.get_system_tools()
    assert len(system_tools) > 0
    assert "system_info" in system_tools


def test_tool_schemas():
    """测试工具schema"""
    schemas = tool_registry.get_tool_schemas()
    assert len(schemas) > 0
    for schema in schemas:
        assert "type" in schema
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]


@pytest.mark.asyncio
async def test_tool_execution():
    """测试工具执行"""
    # 测试系统信息工具
    tool = tool_registry.get_tool("system_info")
    result = await tool.execute()
    assert result is not None
    assert hasattr(result, "status")
    assert hasattr(result, "data")


if __name__ == "__main__":
    pytest.main([__file__]) 