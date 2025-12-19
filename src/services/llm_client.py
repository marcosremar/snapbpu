"""
Cliente para comunicação com LLM (OpenAI, Anthropic).
"""
import json
import logging
from typing import Dict, Optional, Any
import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.llm.default_provider
        self.api_key = settings.llm.openai_api_key if self.provider == "openai" else settings.llm.anthropic_api_key
        self.model = settings.llm.model_name

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Envia prompt e retorna resposta estruturada."""
        if self.provider == "openai":
            return await self._openai_complete(system_prompt, user_prompt, response_format)
        elif self.provider == "anthropic":
            return await self._anthropic_complete(system_prompt, user_prompt)
        else:
            raise ValueError(f"Provider {self.provider} não suportado")

    async def _openai_complete(self, system, user, fmt):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "response_format": fmt or {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.error(f"Erro na chamada OpenAI: {e}")
            raise

    async def _anthropic_complete(self, system, user):
        # Implementação básica Anthropic
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                content = data["content"][0]["text"]
                return json.loads(content)
        except Exception as e:
            logger.error(f"Erro na chamada Anthropic: {e}")
            raise

