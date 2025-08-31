"""
Provider para Anthropic Claude
"""
from typing import Optional
import logging
import httpx
from .adapter import AIAdapter

logger = logging.getLogger(__name__)


class AnthropicProvider(AIAdapter):
    """Provider para modelos Claude da Anthropic"""
    
    def __init__(self, api_key: str, model_name: str):
        super().__init__(api_key, model_name)
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def generate(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.4,
        max_tokens: int = 200
    ) -> str:
        """
        Gera resposta usando Claude
        
        Args:
            system_prompt: Instrução do sistema
            user_prompt: Mensagem do usuário
            temperature: Criatividade (0-1)
            max_tokens: Tamanho máximo
            
        Returns:
            str: Resposta do Claude
        """
        try:
            payload = {
                "model": self.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                content = data.get("content", [])
                
                if content and len(content) > 0:
                    return content[0].get("text", "").strip()
                
                return self._handle_error(
                    Exception("Resposta vazia do Claude")
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout ao chamar Claude")
            return self._handle_error(
                Exception("Timeout"),
                "O sistema demorou para responder. Pode repetir?"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP Claude: {e.response.status_code}")
            return self._handle_error(e)
        except Exception as e:
            logger.error(f"Erro inesperado Claude: {str(e)}")
            return self._handle_error(e)