"""
Provider para OpenAI GPT
"""
from typing import Optional
import logging
import httpx
from .adapter import AIAdapter

logger = logging.getLogger(__name__)


class OpenAIProvider(AIAdapter):
    """Provider para modelos GPT da OpenAI"""
    
    def __init__(self, api_key: str, model_name: str):
        super().__init__(api_key, model_name)
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.4,
        max_tokens: int = 200
    ) -> str:
        """
        Gera resposta usando GPT
        
        Args:
            system_prompt: Instrução do sistema
            user_prompt: Mensagem do usuário
            temperature: Criatividade (0-1)
            max_tokens: Tamanho máximo
            
        Returns:
            str: Resposta do GPT
        """
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.base_url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                choices = data.get("choices", [])
                
                if choices and len(choices) > 0:
                    message = choices[0].get("message", {})
                    return message.get("content", "").strip()
                
                return self._handle_error(
                    Exception("Resposta vazia do GPT")
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout ao chamar GPT")
            return self._handle_error(
                Exception("Timeout"),
                "O sistema demorou para responder. Pode repetir?"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP GPT: {e.response.status_code}")
            return self._handle_error(e)
        except Exception as e:
            logger.error(f"Erro inesperado GPT: {str(e)}")
            return self._handle_error(e)