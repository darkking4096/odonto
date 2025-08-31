"""
Provider para Google Gemini
"""
from typing import Optional
import logging
import httpx
from .adapter import AIAdapter

logger = logging.getLogger(__name__)


class GoogleProvider(AIAdapter):
    """Provider para modelos Gemini do Google"""
    
    def __init__(self, api_key: str, model_name: str):
        super().__init__(api_key, model_name)
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        self.headers = {
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
        Gera resposta usando Gemini
        
        Args:
            system_prompt: Instrução do sistema
            user_prompt: Mensagem do usuário
            temperature: Criatividade (0-1)
            max_tokens: Tamanho máximo
            
        Returns:
            str: Resposta do Gemini
        """
        try:
            # Combina system e user em uma mensagem só para Gemini
            combined_prompt = f"{system_prompt}\n\nUsuário: {user_prompt}\n\nAssistente:"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": combined_prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            url_with_key = f"{self.base_url}?key={self.api_key}"
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url_with_key,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                candidates = data.get("candidates", [])
                
                if candidates and len(candidates) > 0:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts and len(parts) > 0:
                        return parts[0].get("text", "").strip()
                
                return self._handle_error(
                    Exception("Resposta vazia do Gemini")
                )
                
        except httpx.TimeoutException:
            logger.error("Timeout ao chamar Gemini")
            return self._handle_error(
                Exception("Timeout"),
                "O sistema demorou para responder. Pode repetir?"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP Gemini: {e.response.status_code}")
            return self._handle_error(e)
        except Exception as e:
            logger.error(f"Erro inesperado Gemini: {str(e)}")
            return self._handle_error(e)