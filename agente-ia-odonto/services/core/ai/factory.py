"""
Factory para criar provider de IA baseado na configuração
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from .adapter import AIAdapter
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .google_provider import GoogleProvider

logger = logging.getLogger(__name__)
load_dotenv()


class AIFactory:
    """Factory para criar instâncias de providers de IA"""
    
    @staticmethod
    def create_provider() -> Optional[AIAdapter]:
        """
        Cria provider baseado nas variáveis de ambiente
        
        Returns:
            AIAdapter: Instância do provider configurado
        """
        provider_type = os.getenv("AI_PROVIDER", "anthropic").lower()
        
        try:
            if provider_type == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
                
                if not api_key:
                    logger.error("ANTHROPIC_API_KEY não configurada")
                    return None
                
                logger.info(f"Usando provider Anthropic com modelo {model_name}")
                return AnthropicProvider(api_key, model_name)
            
            elif provider_type == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                
                if not api_key:
                    logger.error("OPENAI_API_KEY não configurada")
                    return None
                
                logger.info(f"Usando provider OpenAI com modelo {model_name}")
                return OpenAIProvider(api_key, model_name)
            
            elif provider_type == "google":
                api_key = os.getenv("GOOGLE_API_KEY")
                model_name = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
                
                if not api_key:
                    logger.error("GOOGLE_API_KEY não configurada")
                    return None
                
                logger.info(f"Usando provider Google com modelo {model_name}")
                return GoogleProvider(api_key, model_name)
            
            else:
                logger.error(f"Provider desconhecido: {provider_type}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao criar provider: {str(e)}")
            return None
    
    @staticmethod
    def get_temperature() -> float:
        """
        Obtém temperatura configurada
        
        Returns:
            float: Valor da temperatura (0-1)
        """
        return float(os.getenv("AI_TEMPERATURE", "0.4"))
    
    @staticmethod
    def get_max_tokens() -> int:
        """
        Obtém max_tokens configurado
        
        Returns:
            int: Número máximo de tokens
        """
        return int(os.getenv("AI_MAX_TOKENS", "200"))