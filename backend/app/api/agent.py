from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.agents.text_to_sql import TextToSQLAgent
from app.config import AgentConfig, AppConfig
from app.core.rate_limit import check_rate_limit

router = APIRouter()

agent = TextToSQLAgent(db_url=AppConfig.DATABASE_URL)


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def ask_sql(req: AskRequest, request: Request):
    if not AgentConfig.AGENT_ENABLED:
        raise HTTPException(status_code=503, detail="Agent endpoint is disabled")
    check_rate_limit(request, AgentConfig.RATE_LIMIT_PER_MINUTE)

    result = agent.ask(req.question)

    data_json = (
        result["data"].to_dict(orient="records")
        if result.get("data") is not None else None
    )

    return {
        "question": result["question"],
        "sql": result["sql"],
        "success": result["success"],
        "answer": result["answer"],
        "data": data_json,
        "error": result.get("error"),
    }
