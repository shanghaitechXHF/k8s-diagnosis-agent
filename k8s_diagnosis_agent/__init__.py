"""
K8s诊断Agent

一个强大的Kubernetes集群故障诊断AI Agent
"""

from .core.agent import Agent
from .config import Config

__version__ = "0.1.0"
__author__ = "k8s-diagnosis-agent"

__all__ = ["Agent", "Config"] 