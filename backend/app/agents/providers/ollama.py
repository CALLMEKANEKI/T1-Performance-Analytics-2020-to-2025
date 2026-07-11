import os
from typing import Optional
import requests
from app.agents.base import LLMProvider
from app.config import AgentConfig

class OllamaProvider(LLMProvider):
    """
    Ollama: chạy Llama/Mistral hoàn toàn local, không cần API key.
    Cần cài Ollama: https://ollama.com
    Sau đó: ollama pull llama3.2
    """
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or AgentConfig.OLLAMA_MODEL
        self.base_url = base_url or AgentConfig.OLLAMA_BASE_URL
        self._check_connection()
    
    def _check_connection(self):
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            resp.raise_for_status()
        except Exception:
            raise ConnectionError(
                f"Không kết nối được Ollama tại {self.base_url}. "
                "Đảm bảo Ollama đang chạy: https://ollama.com"
            )
    
    def generate_sql(self, prompt: str, system_prompt: str = None) -> str:
        if not system_prompt:
            system_prompt = "Bạn là SQL expert. Chỉ trả về SQL query, không giải thích thêm."
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": AgentConfig.TEMPERATURE,
                "num_predict": AgentConfig.MAX_TOKENS,
            }
        }
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    
    @property
    def provider_name(self) -> str:
        return f"ollama/{self.model}"