import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def normalize_database_url(raw: str | None) -> str:
    """Resolve DATABASE_URL from env. Fail fast — no credentials hardcoded in source."""
    if not raw or not raw.strip():
        env = os.getenv("ENV", "development").lower()
        if env in ("production", "prod"):
            raise RuntimeError(
                "DATABASE_URL environment variable is required when ENV=production"
            )
        raise RuntimeError(
            "DATABASE_URL is not set. Configure it in .env or docker-compose environment."
        )
    url = raw.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _resolve_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS")
    env = os.getenv("ENV", "development").lower()
    if env in ("production", "prod"):
        if not raw or not raw.strip():
            raise RuntimeError(
                "CORS_ORIGINS environment variable is required when ENV=production"
            )
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    default = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,"
        "https://t1-performance-analytics-2020-to-20.vercel.app"
    )
    origins_raw = raw if raw and raw.strip() else default
    return [origin.strip() for origin in origins_raw.split(",") if origin.strip()]


def _resolve_model1_path() -> Path:
    default = _BACKEND_DIR / "data" / "model1_lgbm.pkl"
    raw = os.getenv("MODEL1_PATH")
    path = Path(raw) if raw else default
    resolved = path.resolve()
    allowed_dir = (_BACKEND_DIR / "data").resolve()
    if not str(resolved).startswith(str(allowed_dir)):
        raise RuntimeError(
            f"MODEL1_PATH must be inside {allowed_dir}, got {resolved}"
        )
    return resolved


class AppConfig:
    # Environment & Database
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    APP_TITLE: str = os.getenv("APP_TITLE", "T1 Analytics API")
    DATABASE_URL: str = normalize_database_url(os.getenv("DATABASE_URL"))

    T1_ID: int = int(os.getenv("T1_TEAM_ID", "1"))

    # Admin / protected endpoints
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

    # Paths
    STATIC_DIR: Path = Path(
        os.getenv("STATIC_DIR", str(_BACKEND_DIR / "static"))
    )
    MODEL1_PATH: Path = _resolve_model1_path()
    MODEL1_SHA256: str = os.getenv("MODEL1_SHA256", "").strip().lower()

    # Database pool
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Cache startup: block until ready when true (default on in production)
    CACHE_WARMUP_BLOCKING: bool = os.getenv(
        "CACHE_WARMUP_BLOCKING",
        "true" if os.getenv("ENV", "development").lower() in ("production", "prod") else "false",
    ).lower() == "true"

    # CORS Origins
    CORS_ORIGINS: list[str] = _resolve_cors_origins()


class AgentConfig(AppConfig):
    # Provider chính: 'claude', 'openai', 'groq', 'openrouter', 'ollama'
    PROVIDER: str = os.getenv("AGENT_PROVIDER", "groq")
    AGENT_ENABLED: bool = os.getenv("AGENT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("AGENT_RATE_LIMIT", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("AGENT_REQUEST_TIMEOUT", "60"))

    # Models
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # Agent settings
    MAX_TOKENS: int = int(os.getenv("AGENT_MAX_TOKENS", "500"))
    TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.1"))
    RESULT_LIMIT: int = int(os.getenv("AGENT_RESULT_LIMIT", "10"))
