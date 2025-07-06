"""
命令行界面
"""
import asyncio
import argparse
import sys
from typing import Optional

from .config import config
from .core import Agent
from .web.app import app


async def interactive_chat():
    """交互式聊天"""
    print("🔧 K8s Diagnosis Agent - 交互式模式")
    print("输入 'quit' 或 'exit' 退出，输入 'help' 查看帮助")
    print("-" * 50)
    
    agent = Agent(config)
    session_id = None
    
    while True:
        try:
            user_input = input("\n用户: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            if not user_input:
                continue
            
            print("助手: ", end="", flush=True)
            
            # 处理用户消息
            async for result in agent.process_message(user_input, session_id):
                if result["type"] == "response_chunk":
                    print(result["data"], end="", flush=True)
                elif result["type"] == "response_complete":
                    session_id = result["session_id"]
                    if not result["data"].get("content"):
                        print(result["data"].get("content", ""))
                elif result["type"] == "error":
                    print(f"\n❌ 错误: {result['data'].get('message', '未知错误')}")
                    break
            
            print()  # 换行
            
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")


def print_help():
    """打印帮助信息"""
    print("""
🔧 K8s Diagnosis Agent 帮助

可用命令：
- help: 显示此帮助信息
- quit/exit/q: 退出程序

示例问题：
- "我的Pod无法启动，请帮我诊断"
- "集群节点状态异常"
- "服务无法访问，请检查网络"
- "查看集群整体状态"

你可以用自然语言描述你遇到的k8s问题，我会帮你诊断和解决。
""")


def run_web_server():
    """运行Web服务器"""
    import uvicorn
    
    print(f"🚀 启动Web服务器...")
    print(f"📍 地址: http://{config.web.host}:{config.web.port}")
    print(f"📚 API文档: http://{config.web.host}:{config.web.port}/docs")
    
    uvicorn.run(
        app,
        host=config.web.host,
        port=config.web.port,
        log_level="info"
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="k8s-diagnosis-agent - AI驱动的Kubernetes集群故障诊断工具"
    )
    
    parser.add_argument(
        "--mode", 
        choices=["web", "cli", "interactive"],
        default="web",
        help="运行模式: web(Web服务器), cli(命令行), interactive(交互式)"
    )
    
    parser.add_argument(
        "--host",
        default=config.web.host,
        help="Web服务器主机地址"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=config.web.port,
        help="Web服务器端口"
    )
    
    parser.add_argument(
        "--config",
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"k8s-diagnosis-agent {config.version}"
    )
    
    args = parser.parse_args()
    
    # 更新配置
    if args.host:
        config.web.host = args.host
    if args.port:
        config.web.port = args.port
    
    # 根据模式运行
    if args.mode == "web":
        run_web_server()
    elif args.mode == "interactive":
        asyncio.run(interactive_chat())
    elif args.mode == "cli":
        print("CLI模式暂未实现，请使用交互式模式")
        sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main() 