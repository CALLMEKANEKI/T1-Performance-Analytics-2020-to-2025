import pandas as pd
from sqlalchemy import text, create_engine
from typing import Tuple, Optional
import re

def validate_sql(sql: str) -> bool:
    """Kiểm tra SQL chỉ chứa SELECT (không DML/DDL)"""
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return False
    dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "MERGE"]
    for kw in dangerous:
        if kw in sql_upper:
            return False
    return True

def execute_sql(engine, sql: str) -> Tuple[bool, Optional[pd.DataFrame], Optional[str]]:
    """Thực thi SQL an toàn, trả về (success, df, error)"""
    if not validate_sql(sql):
        return False, None, "SQL không hợp lệ: chỉ cho phép SELECT"
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.mappings().all())
        return True, df, None
    except Exception as e:
        return False, None, str(e)