from typing import Optional

from openai import OpenAI

from app.agents.base import LLMProvider
from app.config import AgentConfig


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or AgentConfig.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or AgentConfig.OPENAI_MODEL

    def generate_sql(self, prompt: str, system_prompt: str = None) -> str:
        if not system_prompt:
            system_prompt = "Bạn là SQL expert. Chỉ trả về SQL query, không giải thích thêm."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=AgentConfig.TEMPERATURE,
            max_tokens=AgentConfig.MAX_TOKENS,
        )
        return response.choices[0].message.content.strip()

    @property
    def provider_name(self) -> str:
        return "openai"
