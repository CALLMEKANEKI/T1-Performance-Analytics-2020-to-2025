from typing import Optional

from anthropic import Anthropic

from app.agents.base import LLMProvider
from app.config import AgentConfig


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or AgentConfig.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=self.api_key)
        self.model = model or AgentConfig.CLAUDE_MODEL

    def generate_sql(self, prompt: str, system_prompt: str = None) -> str:
        if not system_prompt:
            system_prompt = "Bạn là SQL expert. Chỉ trả về SQL query, không giải thích thêm."

        response = self.client.messages.create(
            model=self.model,
            max_tokens=AgentConfig.MAX_TOKENS,
            temperature=AgentConfig.TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    @property
    def provider_name(self) -> str:
        return "claude"
