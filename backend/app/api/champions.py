# backend/app/api/champions.py

from fastapi import APIRouter
from sqlalchemy import text
import pandas as pd
from app.core.db import DB_URL, engine

router = APIRouter()

@router.get("/champions")
def get_champions():
    query = text("SELECT * FROM champions")
    
    # 2. Thực thi truy vấn bằng cơ chế SQLAlchemy 2.0 an toàn
    with engine.connect() as conn:
        result = conn.execute(query)
        df = pd.DataFrame(result.mappings().all())
        
    return df.to_dict(orient="records")