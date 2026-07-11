from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    @abstractmethod
    def generate_sql(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate SQL query from natural language question.
        
        Args:
            prompt: User question + schema context
            system_prompt: Optional system instruction (default: SQL expert)
        
        Returns:
            SQL query string
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name (e.g., 'claude', 'openai', 'groq')"""
        pass