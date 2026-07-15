"""
Debug cold-start / neutral rolling win rate trên features_model1.parquet.
Chạy từ thư mục backend: python app/pipeline/debug_features.py
"""

from pathlib import Path
import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    DB_URL = _db_url
else:
    DB_URL = "postgresql://t1_user:t1_password@localhost:5433/t1_analytics"

BACKEND_DIR = Path(__file__).resolve().parents[2]
FEATURE_PATH = BACKEND_DIR / "data" / "features_model1.parquet"


def load_game_dates(db_url: str = DB_URL) -> pd.DataFrame:
    engine = create_engine(db_url)
    query = "SELECT id_game, date_played FROM games ORDER BY date_played, id_game"
    dates = pd.read_sql(query, engine)
    dates["date_played"] = pd.to_datetime(dates["date_played"])
    return dates


def print_histogram(series: pd.Series, bins: int = 20) -> None:
    counts, edges = np.histogram(series.dropna(), bins=bins)
    max_count = counts.max() or 1
    bar_width = 50

    print(f"\nHistogram t1_avg_champ_wr ({bins} bins, n={series.notna().sum()})")
    print("-" * 70)
    for i, count in enumerate(counts):
        bar_len = int(round(count / max_count * bar_width))
        bar = "#" * bar_len
        print(f"{edges[i]:6.3f} - {edges[i + 1]:6.3f} | {bar:<{bar_width}} {count:5d}")
    print("-" * 70)
    print(
        f"min={series.min():.4f}  "
        f"mean={series.mean():.4f}  "
        f"median={series.median():.4f}  "
        f"max={series.max():.4f}"
    )


def main() -> None:
    if not FEATURE_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {FEATURE_PATH}. "
            "Chạy features.py trước để tạo parquet."
        )

    df = pd.read_parquet(FEATURE_PATH)
    n = len(df)

    if "t1_avg_champ_wr" not in df.columns:
        raise KeyError("Cột t1_avg_champ_wr không có trong parquet.")

    wr = df["t1_avg_champ_wr"]
    neutral_mask = wr.between(0.48, 0.52, inclusive="both")
    neutral_pct = neutral_mask.mean() * 100

    print("=" * 70)
    print("DEBUG: t1_avg_champ_wr cold-start / neutral 0.5")
    print("=" * 70)
    print(f"Dataset: {n} games")
    print(
        f"\n1) Games co t1_avg_champ_wr trong [0.48, 0.52]: "
        f"{neutral_mask.sum()} / {n} = {neutral_pct:.2f}%"
    )

    print_histogram(wr)

    target_col = "is_t1_win"
    if target_col not in df.columns:
        raise KeyError(f"Cột target {target_col} không có trong parquet.")

    y = df[target_col]
    baseline_acc = y.mean()
    print(f"\n3) Naive baseline (luon predict T1 win): accuracy = {baseline_acc:.4f} ({baseline_acc:.2%})")
    print(f"   (ty le y=1 trong data: {y.sum()} wins / {n} games)")

    print("\n4) 10 games dau tien theo date_played:")
    try:
        dates = load_game_dates()
        view = df.merge(dates, on="id_game", how="left")
        view = view.sort_values(["date_played", "id_game"]).reset_index(drop=True)
    except Exception as exc:
        print(f"   [Canh bao] Khong load duoc date_played tu DB ({exc}).")
        print("   Fallback: sort theo id_game.")
        view = df.sort_values("id_game").reset_index(drop=True)
        view["date_played"] = pd.NaT

    cols = ["date_played", "id_game", "patch_num", "t1_avg_champ_wr", "is_t1_win"]
    cols = [c for c in cols if c in view.columns]
    print(view.loc[:9, cols].to_string(index=True))


if __name__ == "__main__":
    main()
