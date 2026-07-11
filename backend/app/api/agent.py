from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.text_to_sql import TextToSQLAgent
from app.pipeline.features import DB_URL

router = APIRouter()

# Khởi tạo agent 1 lần duy nhất
agent = TextToSQLAgent(db_url=DB_URL)  # provider sẽ được lấy từ config

class AskRequest(BaseModel):
    question: str

@router.post("/ask")
def ask_sql(req: AskRequest):
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