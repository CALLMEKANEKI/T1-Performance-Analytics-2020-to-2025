# backend/app/api/champions.py

from fastapi import APIRouter
from sqlalchemy import create_engine, text
import pandas as pd
from app.core.db import DB_URL  

engine = create_engine(DB_URL)

router = APIRouter()

@router.get("/champions")
def get_champions():
    query = text("SELECT * FROM champions")
    
    with engine.connect() as conn:
        result = conn.execute(query)
        df = pd.DataFrame(result.mappings().all())
        
    return df.to_dict(orient="records")