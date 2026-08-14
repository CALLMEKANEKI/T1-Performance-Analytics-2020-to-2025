import math
from typing import Any, List

import pandas as pd


def _nan_to_none(val: Any) -> Any:
    """Convert NaN/inf float values to None for JSON serialization."""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def df_to_records(df: pd.DataFrame) -> List[dict]:
    """Convert DataFrame to list[dict] with NaN/inf replaced by None."""
    records = df.where(df.notna(), other=None).to_dict(orient="records")
    return [{k: _nan_to_none(v) for k, v in row.items()} for row in records]
