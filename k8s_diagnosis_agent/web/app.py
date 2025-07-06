"""
Web应用主程序
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from ..config import config
from .api import router


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=config.app_name,
        description=config.description,
        version=config.version,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.web.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加API路由
    app.include_router(router, prefix="/api/v1")
    
    # 静态文件服务
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # 主页
    @app.get("/", response_class=HTMLResponse)
    async def index():
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>K8s Diagnosis Agent</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                    margin-bottom: 30px;
                }
                .chat-container {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    height: 400px;
                    overflow-y: auto;
                    padding: 15px;
                    margin-bottom: 20px;
                    background: #fafafa;
                }
                .input-container {
                    display: flex;
                    gap: 10px;
                }
                input[type="text"] {
                    flex: 1;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 16px;
                }
                button {
                    padding: 12px 24px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                }
                button:hover {
                    background-color: #0056b3;
                }
                .message {
                    margin-bottom: 15px;
                    padding: 10px;
                    border-radius: 6px;
                }
                .user-message {
                    background-color: #e3f2fd;
                    text-align: right;
                }
                .assistant-message {
                    background-color: #f1f8e9;
                }
                .error-message {
                    background-color: #ffebee;
                    color: #c62828;
                }
                .api-info {
                    margin-top: 30px;
                    padding: 20px;
                    background-color: #f8f9fa;
                    border-radius: 6px;
                }
                .api-info h3 {
                    margin-top: 0;
                    color: #495057;
                }
                .api-info ul {
                    list-style-type: none;
                    padding: 0;
                }
                .api-info li {
                    margin: 10px 0;
                    padding: 8px;
                    background: white;
                    border-radius: 4px;
                    border-left: 4px solid #007bff;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 K8s Diagnosis Agent</h1>
                <p style="text-align: center; color: #666; margin-bottom: 30px;">
                    专业的Kubernetes集群故障诊断AI助手
                </p>
                
                <div class="chat-container" id="chatContainer">
                    <div class="message assistant-message">
                        <strong>助手:</strong> 您好！我是K8s诊断助手，可以帮助您诊断和解决Kubernetes集群问题。请描述您遇到的问题。
                    </div>
                </div>
                
                <div class="input-container">
                    <input type="text" id="messageInput" placeholder="请输入您的问题..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">发送</button>
                </div>
                
                <div class="api-info">
                    <h3>🔗 API接口</h3>
                    <ul>
                        <li><strong>POST /api/v1/chat</strong> - 聊天接口</li>
                        <li><strong>POST /api/v1/tool</strong> - 执行工具</li>
                        <li><strong>GET /api/v1/tools</strong> - 获取可用工具</li>
                        <li><strong>GET /api/v1/status</strong> - 系统状态</li>
                        <li><strong>GET /docs</strong> - API文档</li>
                    </ul>
                </div>
            </div>
            
            <script>
                let sessionId = null;
                
                async function sendMessage() {
                    const input = document.getElementById('messageInput');
                    const message = input.value.trim();
                    
                    if (!message) return;
                    
                    // 显示用户消息
                    addMessage('user', message);
                    input.value = '';
                    
                    try {
                        const response = await fetch('/api/v1/chat', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                message: message,
                                session_id: sessionId,
                                stream: false
                            })
                        });
                        
                        const result = await response.json();
                        
                        if (result.session_id) {
                            sessionId = result.session_id;
                        }
                        
                        if (result.type === 'response_complete') {
                            addMessage('assistant', result.data.content);
                        } else if (result.type === 'error') {
                            addMessage('error', result.data.message || '发生错误');
                        }
                        
                    } catch (error) {
                        addMessage('error', '网络错误: ' + error.message);
                    }
                }
                
                function addMessage(type, content) {
                    const chatContainer = document.getElementById('chatContainer');
                    const messageDiv = document.createElement('div');
                    messageDiv.className = `message ${type}-message`;
                    
                    const label = type === 'user' ? '用户' : type === 'assistant' ? '助手' : '错误';
                    messageDiv.innerHTML = `<strong>${label}:</strong> ${content}`;
                    
                    chatContainer.appendChild(messageDiv);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
                
                function handleKeyPress(event) {
                    if (event.key === 'Enter') {
                        sendMessage();
                    }
                }
            </script>
        </body>
        </html>
        """
    
    return app


# 创建应用实例
app = create_app() 