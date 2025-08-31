"""
Interface base para adapters de IA
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AIAdapter(ABC):
    """Interface base para providers de IA"""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
    
    @abstractmethod
    def generate(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.4,
        max_tokens: int = 200
    ) -> str:
        """
        Gera resposta usando o LLM
        
        Args:
            system_prompt: Instrução do sistema
            user_prompt: Mensagem do usuário
            temperature: Criatividade da resposta (0-1)
            max_tokens: Tamanho máximo da resposta
            
        Returns:
            str: Resposta gerada pelo modelo
        """
        pass
    
    def _handle_error(self, error: Exception, fallback: str = "Desculpe, não entendi. Pode repetir?") -> str:
        """
        Trata erros com fallback
        
        Args:
            error: Exceção capturada
            fallback: Mensagem padrão de erro
            
        Returns:
            str: Mensagem de fallback
        """
        logger.error(f"Erro no provider {self.__class__.__name__}: {str(error)}")
        return fallback