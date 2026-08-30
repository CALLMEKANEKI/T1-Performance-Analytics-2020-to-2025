import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_DIR.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _env_value(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else str(value)


def _env_bool(name: str, default: str = "false") -> bool:
    return _env_value(name, default).lower() == "true"


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
    PROVIDER: str = _env_value("AGENT_PROVIDER").lower()
    AGENT_ENABLED: bool = _env_bool("AGENT_ENABLED", "true")
    RATE_LIMIT_PER_MINUTE: int = int(_env_value("AGENT_RATE_LIMIT", "10"))
    REQUEST_TIMEOUT: int = int(_env_value("AGENT_REQUEST_TIMEOUT", "60"))

    # Models: read from environment only; no hardcoded model names in source
    GROQ_MODEL: str = _env_value("GROQ_MODEL")
    CLAUDE_MODEL: str = _env_value("CLAUDE_MODEL")
    OPENAI_MODEL: str = _env_value("OPENAI_MODEL")
    OPENROUTER_MODEL: str = _env_value("OPENROUTER_MODEL")
    OLLAMA_MODEL: str = _env_value("OLLAMA_MODEL")
    OLLAMA_BASE_URL: str = _env_value("OLLAMA_BASE_URL", "http://localhost:11434")
    OPENROUTER_BASE_URL: str = _env_value("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # API Keys
    GROQ_API_KEY: str = _env_value("GROQ_API_KEY")
    ANTHROPIC_API_KEY: str = _env_value("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: str = _env_value("OPENAI_API_KEY")
    OPENROUTER_API_KEY: str = _env_value("OPENROUTER_API_KEY")

    # Agent settings
    MAX_TOKENS: int = int(_env_value("AGENT_MAX_TOKENS", "500"))
    TEMPERATURE: float = float(_env_value("AGENT_TEMPERATURE", "0.1"))
    RESULT_LIMIT: int = int(_env_value("AGENT_RESULT_LIMIT", "10"))
