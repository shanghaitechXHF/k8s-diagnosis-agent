"""
Kubeconfig数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import yaml
import base64
import tempfile
import os
from pathlib import Path


@dataclass
class ClusterInfo:
    """集群信息"""
    name: str
    server: str
    certificate_authority_data: Optional[str] = None
    certificate_authority: Optional[str] = None
    insecure_skip_tls_verify: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserInfo:
    """用户信息"""
    name: str
    client_certificate_data: Optional[str] = None
    client_key_data: Optional[str] = None
    client_certificate: Optional[str] = None
    client_key: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    auth_provider: Optional[Dict[str, Any]] = None
    exec: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextInfo:
    """上下文信息"""
    name: str
    cluster: str
    user: str
    namespace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KubeconfigInfo:
    """Kubeconfig信息"""
    id: str
    name: str
    description: str = ""
    clusters: List[ClusterInfo] = field(default_factory=list)
    users: List[UserInfo] = field(default_factory=list)
    contexts: List[ContextInfo] = field(default_factory=list)
    current_context: Optional[str] = None
    source: str = "user_provided"  # user_provided, file, environment
    source_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_kubeconfig_dict(self) -> Dict[str, Any]:
        """转换为标准kubeconfig字典格式"""
        config = {
            'apiVersion': 'v1',
            'kind': 'Config',
            'clusters': [],
            'users': [],
            'contexts': [],
            'current-context': self.current_context
        }
        
        # 添加集群
        for cluster in self.clusters:
            cluster_config = {
                'name': cluster.name,
                'cluster': {
                    'server': cluster.server
                }
            }
            
            if cluster.certificate_authority_data:
                cluster_config['cluster']['certificate-authority-data'] = cluster.certificate_authority_data
            elif cluster.certificate_authority:
                cluster_config['cluster']['certificate-authority'] = cluster.certificate_authority
            
            if cluster.insecure_skip_tls_verify:
                cluster_config['cluster']['insecure-skip-tls-verify'] = True
            
            config['clusters'].append(cluster_config)
        
        # 添加用户
        for user in self.users:
            user_config = {
                'name': user.name,
                'user': {}
            }
            
            if user.client_certificate_data:
                user_config['user']['client-certificate-data'] = user.client_certificate_data
            elif user.client_certificate:
                user_config['user']['client-certificate'] = user.client_certificate
            
            if user.client_key_data:
                user_config['user']['client-key-data'] = user.client_key_data
            elif user.client_key:
                user_config['user']['client-key'] = user.client_key
            
            if user.token:
                user_config['user']['token'] = user.token
            
            if user.username and user.password:
                user_config['user']['username'] = user.username
                user_config['user']['password'] = user.password
            
            if user.auth_provider:
                user_config['user']['auth-provider'] = user.auth_provider
            
            if user.exec:
                user_config['user']['exec'] = user.exec
            
            config['users'].append(user_config)
        
        # 添加上下文
        for context in self.contexts:
            context_config = {
                'name': context.name,
                'context': {
                    'cluster': context.cluster,
                    'user': context.user
                }
            }
            
            if context.namespace:
                context_config['context']['namespace'] = context.namespace
            
            config['contexts'].append(context_config)
        
        return config
    
    def to_yaml(self) -> str:
        """转换为YAML格式的kubeconfig"""
        config_dict = self.to_kubeconfig_dict()
        return yaml.dump(config_dict, default_flow_style=False)
    
    def save_to_file(self, file_path: str) -> bool:
        """保存kubeconfig到文件"""
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_yaml())
            
            self.source_path = file_path
            self.updated_at = datetime.now()
            return True
            
        except Exception:
            return False
    
    def create_temp_file(self) -> str:
        """创建临时kubeconfig文件"""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.kubeconfig',
            delete=False,
            encoding='utf-8'
        )
        
        temp_file.write(self.to_yaml())
        temp_file.close()
        
        return temp_file.name
    
    def get_cluster_by_name(self, name: str) -> Optional[ClusterInfo]:
        """根据名称获取集群信息"""
        for cluster in self.clusters:
            if cluster.name == name:
                return cluster
        return None
    
    def get_user_by_name(self, name: str) -> Optional[UserInfo]:
        """根据名称获取用户信息"""
        for user in self.users:
            if user.name == name:
                return user
        return None
    
    def get_context_by_name(self, name: str) -> Optional[ContextInfo]:
        """根据名称获取上下文信息"""
        for context in self.contexts:
            if context.name == name:
                return context
        return None
    
    def get_current_context_info(self) -> Optional[ContextInfo]:
        """获取当前上下文信息"""
        if not self.current_context:
            return None
        return self.get_context_by_name(self.current_context)
    
    def get_current_cluster_info(self) -> Optional[ClusterInfo]:
        """获取当前集群信息"""
        context = self.get_current_context_info()
        if not context:
            return None
        return self.get_cluster_by_name(context.cluster)
    
    def get_current_user_info(self) -> Optional[UserInfo]:
        """获取当前用户信息"""
        context = self.get_current_context_info()
        if not context:
            return None
        return self.get_user_by_name(context.user)
    
    def validate(self) -> List[str]:
        """验证kubeconfig配置"""
        errors = []
        
        # 检查基本信息
        if not self.name:
            errors.append("缺少配置名称")
        
        if not self.clusters:
            errors.append("缺少集群配置")
        
        if not self.users:
            errors.append("缺少用户配置")
        
        if not self.contexts:
            errors.append("缺少上下文配置")
        
        # 检查当前上下文
        if self.current_context:
            if not self.get_context_by_name(self.current_context):
                errors.append(f"当前上下文 '{self.current_context}' 不存在")
        
        # 检查上下文引用
        for context in self.contexts:
            if not self.get_cluster_by_name(context.cluster):
                errors.append(f"上下文 '{context.name}' 引用的集群 '{context.cluster}' 不存在")
            
            if not self.get_user_by_name(context.user):
                errors.append(f"上下文 '{context.name}' 引用的用户 '{context.user}' 不存在")
        
        # 检查集群配置
        for cluster in self.clusters:
            if not cluster.server:
                errors.append(f"集群 '{cluster.name}' 缺少服务器地址")
            
            if not cluster.certificate_authority_data and not cluster.certificate_authority and not cluster.insecure_skip_tls_verify:
                errors.append(f"集群 '{cluster.name}' 缺少证书配置")
        
        # 检查用户配置
        for user in self.users:
            has_auth = any([
                user.client_certificate_data and user.client_key_data,
                user.client_certificate and user.client_key,
                user.token,
                user.username and user.password,
                user.auth_provider,
                user.exec
            ])
            
            if not has_auth:
                errors.append(f"用户 '{user.name}' 缺少认证配置")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'clusters': [
                {
                    'name': cluster.name,
                    'server': cluster.server,
                    'insecure_skip_tls_verify': cluster.insecure_skip_tls_verify,
                    'metadata': cluster.metadata
                }
                for cluster in self.clusters
            ],
            'users': [
                {
                    'name': user.name,
                    'has_certificate': bool(user.client_certificate_data or user.client_certificate),
                    'has_key': bool(user.client_key_data or user.client_key),
                    'has_token': bool(user.token),
                    'has_basic_auth': bool(user.username and user.password),
                    'has_auth_provider': bool(user.auth_provider),
                    'has_exec': bool(user.exec),
                    'metadata': user.metadata
                }
                for user in self.users
            ],
            'contexts': [
                {
                    'name': context.name,
                    'cluster': context.cluster,
                    'user': context.user,
                    'namespace': context.namespace,
                    'metadata': context.metadata
                }
                for context in self.contexts
            ],
            'current_context': self.current_context,
            'source': self.source,
            'source_path': self.source_path,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'tags': self.tags,
            'metadata': self.metadata,
            'validation_errors': self.validate()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KubeconfigInfo':
        """从字典创建对象"""
        # 解析集群
        clusters = []
        for cluster_data in data.get('clusters', []):
            cluster = ClusterInfo(
                name=cluster_data['name'],
                server=cluster_data['server'],
                certificate_authority_data=cluster_data.get('certificate_authority_data'),
                certificate_authority=cluster_data.get('certificate_authority'),
                insecure_skip_tls_verify=cluster_data.get('insecure_skip_tls_verify', False),
                metadata=cluster_data.get('metadata', {})
            )
            clusters.append(cluster)
        
        # 解析用户
        users = []
        for user_data in data.get('users', []):
            user = UserInfo(
                name=user_data['name'],
                client_certificate_data=user_data.get('client_certificate_data'),
                client_key_data=user_data.get('client_key_data'),
                client_certificate=user_data.get('client_certificate'),
                client_key=user_data.get('client_key'),
                token=user_data.get('token'),
                username=user_data.get('username'),
                password=user_data.get('password'),
                auth_provider=user_data.get('auth_provider'),
                exec=user_data.get('exec'),
                metadata=user_data.get('metadata', {})
            )
            users.append(user)
        
        # 解析上下文
        contexts = []
        for context_data in data.get('contexts', []):
            context = ContextInfo(
                name=context_data['name'],
                cluster=context_data['cluster'],
                user=context_data['user'],
                namespace=context_data.get('namespace'),
                metadata=context_data.get('metadata', {})
            )
            contexts.append(context)
        
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            clusters=clusters,
            users=users,
            contexts=contexts,
            current_context=data.get('current_context'),
            source=data.get('source', 'user_provided'),
            source_path=data.get('source_path'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            is_active=data.get('is_active', True),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def from_kubeconfig_dict(cls, config_dict: Dict[str, Any], id: str, name: str) -> 'KubeconfigInfo':
        """从标准kubeconfig字典创建对象"""
        # 解析集群
        clusters = []
        for cluster_config in config_dict.get('clusters', []):
            cluster_info = cluster_config.get('cluster', {})
            cluster = ClusterInfo(
                name=cluster_config['name'],
                server=cluster_info.get('server', ''),
                certificate_authority_data=cluster_info.get('certificate-authority-data'),
                certificate_authority=cluster_info.get('certificate-authority'),
                insecure_skip_tls_verify=cluster_info.get('insecure-skip-tls-verify', False)
            )
            clusters.append(cluster)
        
        # 解析用户
        users = []
        for user_config in config_dict.get('users', []):
            user_info = user_config.get('user', {})
            user = UserInfo(
                name=user_config['name'],
                client_certificate_data=user_info.get('client-certificate-data'),
                client_key_data=user_info.get('client-key-data'),
                client_certificate=user_info.get('client-certificate'),
                client_key=user_info.get('client-key'),
                token=user_info.get('token'),
                username=user_info.get('username'),
                password=user_info.get('password'),
                auth_provider=user_info.get('auth-provider'),
                exec=user_info.get('exec')
            )
            users.append(user)
        
        # 解析上下文
        contexts = []
        for context_config in config_dict.get('contexts', []):
            context_info = context_config.get('context', {})
            context = ContextInfo(
                name=context_config['name'],
                cluster=context_info.get('cluster', ''),
                user=context_info.get('user', ''),
                namespace=context_info.get('namespace')
            )
            contexts.append(context)
        
        return cls(
            id=id,
            name=name,
            clusters=clusters,
            users=users,
            contexts=contexts,
            current_context=config_dict.get('current-context')
        )
    
    @classmethod
    def from_yaml_file(cls, file_path: str, id: str, name: str) -> 'KubeconfigInfo':
        """从YAML文件创建对象"""
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        kubeconfig = cls.from_kubeconfig_dict(config_dict, id, name)
        kubeconfig.source = 'file'
        kubeconfig.source_path = file_path
        
        return kubeconfig 