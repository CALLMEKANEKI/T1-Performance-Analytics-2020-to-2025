import os
from typing import Optional
from openai import OpenAI 
from app.agents.base import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def generate_sql(self, prompt: str, system_prompt: str = None) -> str:
        if not system_prompt:
            system_prompt = "Bạn là SQL expert. Chỉ trả về SQL query, không giải thích thêm."
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    
    @property
    def provider_name(self) -> str:
        return "openai"