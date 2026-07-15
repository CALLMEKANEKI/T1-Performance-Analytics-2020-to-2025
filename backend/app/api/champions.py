# backend/app/api/champions.py

from fastapi import APIRouter  # <--- Đảm bảo đã import APIRouter
from sqlalchemy import text
import pandas as pd

router = APIRouter()

@router.get("/champions")
def get_champions():
    query = text("SELECT * FROM champions")
    
    # Giữ nguyên phần kết nối an toàn chúng ta vừa tối ưu
    with engine.connect() as conn:
        result = conn.execute(query)
        df = pd.DataFrame(result.mappings().all())
        
    return df.to_dict(orient="records")