#!/usr/bin/env python3
"""
测试 LangChain Agent 模块
验证所有组件是否正常工作
"""

import sys
import os
import asyncio
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试导入"""
    print("=== 测试导入 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import (
            K8sDiagnosisAgent,
            create_langchain_tools,
            K8sToolWrapper,
            K8sDiagnosisMemory,
            DiagnosisChain,
            K8sAnalysisChain,
            K8sSummaryChain,
            K8sPromptManager
        )
        print("✅ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_config_creation():
    """测试配置创建"""
    print("\n=== 测试配置创建 ===")
    try:
        from k8s_diagnosis_agent.config import Config
        
        # 创建最小配置
        config = Config(
            llm=Config.LLMConfig(
                default_model="gpt-3.5-turbo",
                openai_api_key="test-key",
                openai_model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=1000,
                timeout=30
            ),
            kubernetes=Config.KubernetesConfig(
                config_path="",
                context="",
                namespace="default"
            )
        )
        print("✅ 配置创建成功")
        return config
    except Exception as e:
        print(f"❌ 配置创建失败: {e}")
        return None

def test_prompt_manager(config):
    """测试提示词管理器"""
    print("\n=== 测试提示词管理器 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import K8sPromptManager
        
        prompt_manager = K8sPromptManager(config)
        
        # 测试各种提示词生成
        system_prompt = prompt_manager.create_system_prompt()
        print(f"✅ 系统提示词生成成功 (长度: {len(system_prompt)})")
        
        diagnosis_prompt = prompt_manager.create_diagnosis_prompt("Pod一直处于Pending状态")
        print(f"✅ 诊断提示词生成成功 (长度: {len(diagnosis_prompt)})")
        
        agent_prompt = prompt_manager.get_agent_prompt()
        print(f"✅ Agent提示词生成成功")
        
        return True
    except Exception as e:
        print(f"❌ 提示词管理器测试失败: {e}")
        return False

def test_memory_system(config):
    """测试记忆系统"""
    print("\n=== 测试记忆系统 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import K8sDiagnosisMemory
        
        memory = K8sDiagnosisMemory(config)
        
        # 测试添加交互
        memory.add_interaction(
            "Pod一直处于Pending状态",
            "我来帮您诊断这个问题",
            {"session_id": "test-123"}
        )
        print("✅ 交互添加成功")
        
        # 测试获取相关历史
        history = memory.get_relevant_history("Pod状态问题")
        print(f"✅ 相关历史获取成功 (数量: {len(history)})")
        
        # 测试获取统计信息
        stats = memory.get_memory_stats()
        print(f"✅ 记忆统计获取成功: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ 记忆系统测试失败: {e}")
        return False

def test_tools_creation(config):
    """测试工具创建"""
    print("\n=== 测试工具创建 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import create_langchain_tools
        
        tools = create_langchain_tools(config)
        print(f"✅ 工具创建成功 (数量: {len(tools)})")
        
        # 检查工具名称
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "k8s_cluster_info",
            "k8s_pod_info", 
            "k8s_node_info",
            "k8s_events",
            "k8s_logs",
            "system_info"
        ]
        
        for expected in expected_tools:
            if expected in tool_names:
                print(f"  ✅ {expected}")
            else:
                print(f"  ❌ {expected} 缺失")
        
        return True
    except Exception as e:
        print(f"❌ 工具创建测试失败: {e}")
        return False

def test_chains(config):
    """测试链式调用"""
    print("\n=== 测试链式调用 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import DiagnosisChain, K8sAnalysisChain, K8sSummaryChain
        
        # 测试诊断链
        diagnosis_chain = DiagnosisChain(config)
        print("✅ 诊断链创建成功")
        
        # 测试分析链
        analysis_chain = K8sAnalysisChain(config)
        print("✅ 分析链创建成功")
        
        # 测试总结链
        summary_chain = K8sSummaryChain(config)
        print("✅ 总结链创建成功")
        
        return True
    except Exception as e:
        print(f"❌ 链式调用测试失败: {e}")
        return False

async def test_agent_creation(config):
    """测试Agent创建"""
    print("\n=== 测试Agent创建 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import K8sDiagnosisAgent
        
        agent = K8sDiagnosisAgent(config)
        print("✅ Agent创建成功")
        
        # 测试获取LLM信息
        llm_info = agent.get_llm_info()
        print(f"✅ LLM信息获取成功: {llm_info}")
        
        # 测试获取可用工具
        tools_info = await agent.get_available_tools()
        print(f"✅ 可用工具获取成功 (数量: {len(tools_info.get('tools', []))})")
        
        return True
    except Exception as e:
        print(f"❌ Agent创建测试失败: {e}")
        return False

async def test_basic_functionality(config):
    """测试基本功能"""
    print("\n=== 测试基本功能 ===")
    try:
        from k8s_diagnosis_agent.langchain_agent import K8sDiagnosisAgent
        
        agent = K8sDiagnosisAgent(config)
        
        # 测试处理消息（非流式）
        print("测试消息处理...")
        async for result in agent.process_message("测试消息", session_id="test-123"):
            print(f"✅ 消息处理结果: {result.get('type', 'unknown')}")
            break  # 只取第一个结果
        
        return True
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试 LangChain Agent 模块...")
    
    # 测试导入
    if not test_imports():
        print("❌ 导入测试失败，退出")
        return
    
    # 测试配置创建
    config = test_config_creation()
    if not config:
        print("❌ 配置创建失败，退出")
        return
    
    # 测试各个组件
    tests = [
        test_prompt_manager,
        test_memory_system,
        test_tools_creation,
        test_chains
    ]
    
    for test_func in tests:
        if not test_func(config):
            print(f"❌ {test_func.__name__} 测试失败")
    
    # 测试异步功能
    async def run_async_tests():
        await test_agent_creation(config)
        await test_basic_functionality(config)
    
    asyncio.run(run_async_tests())
    
    print("\n=== 测试完成 ===")
    print("如果看到所有 ✅ 标记，说明模块工作正常")
    print("如果有 ❌ 标记，请检查相应的错误信息")

if __name__ == "__main__":
    main() 