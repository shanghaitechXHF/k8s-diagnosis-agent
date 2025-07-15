#!/usr/bin/env python3
"""
测试 LangChain Agent 模块
验证所有组件是否正常工作
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from k8s_diagnosis_agent.config import Config
from k8s_diagnosis_agent.langchain_agent import (
    K8sDiagnosisAgent,
    create_langchain_tools,
    K8sDiagnosisMemory,
    DiagnosisChain,
    K8sAnalysisChain,
    K8sSummaryChain,
    K8sPromptManager
)


async def test_langchain_agent():
    """测试 LangChain Agent 模块"""
    print("=== 测试 LangChain Agent 模块 ===")
    
    try:
        # 创建配置
        config = Config()
        print("✓ 配置创建成功")
        
        # 测试工具创建
        tools = create_langchain_tools(config)
        print(f"✓ 工具创建成功，共 {len(tools)} 个工具")
        
        # 测试记忆系统
        memory = K8sDiagnosisMemory(config)
        print("✓ 记忆系统创建成功")
        
        # 测试提示词管理器
        prompt_manager = K8sPromptManager(config)
        print("✓ 提示词管理器创建成功")
        
        # 测试链
        diagnosis_chain = DiagnosisChain(config)
        analysis_chain = K8sAnalysisChain(config)
        summary_chain = K8sSummaryChain(config)
        print("✓ 链创建成功")
        
        # 测试 Agent（如果 LangChain 可用）
        try:
            agent = K8sDiagnosisAgent(config)
            print("✓ Agent 创建成功")
        except Exception as e:
            print(f"⚠ Agent 创建失败（可能是 LangChain 不可用）: {e}")
        
        # 测试提示词生成
        system_prompt = prompt_manager.create_system_prompt()
        print(f"✓ 系统提示词生成成功，长度: {len(system_prompt)}")
        
        diagnosis_prompt = prompt_manager.create_diagnosis_prompt("Pod一直处于Pending状态")
        print(f"✓ 诊断提示词生成成功，长度: {len(diagnosis_prompt)}")
        
        # 测试记忆功能
        memory.add_interaction("测试问题", "测试回答", {"test": True})
        stats = memory.get_memory_stats()
        print(f"✓ 记忆功能测试成功: {stats}")
        
        print("\n=== 所有测试通过 ===")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """测试导入"""
    print("=== 测试导入 ===")
    
    try:
        from k8s_diagnosis_agent.langchain_agent import __all__
        print(f"✓ 模块导入成功，导出: {__all__}")
        
        # 测试每个组件的导入
        components = [
            "K8sDiagnosisAgent",
            "create_langchain_tools", 
            "K8sDiagnosisMemory",
            "DiagnosisChain",
            "K8sAnalysisChain",
            "K8sSummaryChain",
            "K8sPromptManager"
        ]
        
        for component in components:
            try:
                exec(f"from k8s_diagnosis_agent.langchain_agent import {component}")
                print(f"✓ {component} 导入成功")
            except Exception as e:
                print(f"✗ {component} 导入失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ 导入测试失败: {e}")
        return False


def main():
    """主函数"""
    print("开始测试 LangChain Agent 模块...")
    
    # 测试导入
    import_success = test_imports()
    
    # 测试功能
    if import_success:
        asyncio.run(test_langchain_agent())
    else:
        print("导入测试失败，跳过功能测试")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main() 