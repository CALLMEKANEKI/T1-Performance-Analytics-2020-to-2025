import os
from dotenv import load_dotenv
load_dotenv()

class AgentConfig:
    # Provider chính: 'claude', 'openai', 'groq', 'openrouter', 'ollama'
    PROVIDER: str = os.getenv("AGENT_PROVIDER", "groq")
    
    # Models
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Agent settings
    MAX_TOKENS: int = int(os.getenv("AGENT_MAX_TOKENS", "500"))
    TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.1"))
    RESULT_LIMIT: int = int(os.getenv("AGENT_RESULT_LIMIT", "10"))