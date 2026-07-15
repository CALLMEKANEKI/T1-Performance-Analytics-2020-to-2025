from sqlalchemy import text  
import pandas as pd

@router.get("/champions")
def get_champions():
    query = text("SELECT * FROM champions") # Bọc bằng text()
    
    with engine.connect() as conn:
        result = conn.execute(query)
        df = pd.DataFrame(result.mappings().all())
        
    return df.to_dict(orient="records")