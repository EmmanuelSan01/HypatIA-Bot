"""
Factory para crear y configurar agentes Langroid
"""
from langroid import ChatAgent, Task, ChatAgentConfig

from app.agents.config import langroid_config
from .main_agent import MainHypatiaAgent

class HypatiaAgentFactory:
    """Factory para crear y configurar agentes Langroid"""
    
    @staticmethod
    def create_main_agent() -> MainHypatiaAgent:
        """Crea el agente principal configurado"""
        config = ChatAgentConfig(
            llm=langroid_config.LLM_CONFIG,
            system_message=langroid_config.SYSTEM_PROMPTS["main_agent"],
            name="HypatIA",
        )
        
        return MainHypatiaAgent(config)
    
    @staticmethod
    def create_task_for_agent(agent: ChatAgent, user_message: str) -> Task:
        """Crea una tarea Langroid para el agente"""
        task = Task(
            agent=agent,
            name="HypatiaConversation",
            system_message=agent.config.system_message,
            llm_delegate=True,
            single_round=False,
        )
        
        return task
