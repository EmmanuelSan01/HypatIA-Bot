"""
Módulo principal de agentes - punto de entrada unificado
"""

# Importaciones principales
from .main_agent import MainHypatiaAgent
from .factory import HypatiaAgentFactory
from .specialized_agents import KnowledgeAgent, SalesAgent, AnalyticsAgent
from .tools import CourseSearchTool, PromotionSearchTool, UserHistoryTool
from .utils import safe_stringify

# Exportar las clases principales que se usan externamente
__all__ = [
    'MainHypatiaAgent',
    'HypatiaAgentFactory',
    'KnowledgeAgent',
    'SalesAgent', 
    'AnalyticsAgent',
    'CourseSearchTool',
    'PromotionSearchTool',
    'UserHistoryTool',
    'safe_stringify'
]
