"""
Model 4: Champion Synergy Network
Tính synergy score cho mỗi cặp champion T1 pick cùng team.
Output: 2 file parquet — by-year và all-time.

Chạy từ thư mục backend/:
    python -m app.pipeline.model4_synergy_network
"""

import json
from itertools import combinations
from pathlib import Path

import pandas as pd

from app.pipeline.features import DB_URL, load_raw_data

# ─── Constants ────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parents[2]
OUTPUT_BY_YEAR = BACKEND_DIR / "data" / "model4_synergy_by_year.parquet"
OUTPUT_ALLTIME = BACKEND_DIR / "data" / "model4_synergy_alltime.parquet"
CHAMPION_TYPES_PATH = BACKEND_DIR / "data" / "champion_types.json"

# Bayesian smoothing alpha (giống Model 1)
ALPHA = 3
# Threshold tối thiểu: chỉ giữ pairs có >= MIN_GAMES
MIN_GAMES = 5


# ─── Load champion type mapping ───────────────────────────────────────────────
def load_champion_types() -> dict[str, str]:
    """Đọc champion_types.json → dict {champion_name: type}."""
    # Thử cả 2 đường dẫn phổ biến trong dự án
    paths_to_try = [
        CHAMPION_TYPES_PATH,
        BACKEND_DIR / "data" / "champions" / "champion_types.json",
    ]
    for path in paths_to_try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    print("  [WARN] champion_types.json không tìm thấy — type_a/type_b sẽ là 'unknown'")
    return {}


# ─── Generate champion pairs từ T1 picks ──────────────────────────────────────
def generate_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Với mỗi game, lấy 5 champion T1 picks và tạo tất cả C(5,2) = 10 cặp.
    Đảm bảo champion_a < champion_b (alphabetical) để tránh duplicate.
    """
    records = []

    # Thêm cột year từ date_played
    df = df.copy()
    df["year"] = df["date_played"].dt.year

    # Group theo từng game
    for id_game, game_df in df.groupby("id_game"):
        t1_picks = game_df[game_df["team_name"] == "T1"]

        # Lấy danh sách champion + metadata game
        champs = t1_picks["champion_name"].dropna().tolist()
        if len(champs) < 2:
            continue  # Bỏ qua game thiếu data

        is_win = int(t1_picks["is_win"].iloc[0])
        year = int(t1_picks["year"].iloc[0])

        # Tạo tất cả cặp, sắp xếp để (A,B) luôn nhất quán
        for champ_a, champ_b in combinations(sorted(set(champs)), 2):
            records.append({
                "id_game": id_game,
                "champion_a": champ_a,
                "champion_b": champ_b,
                "is_win": is_win,
                "year": year,
            })

    pairs_df = pd.DataFrame(records)
    print(f"  Tổng số champion pair rows: {len(pairs_df):,} "
          f"(từ {pairs_df['id_game'].nunique():,} games)")
    return pairs_df


# ─── Tính synergy stats ────────────────────────────────────────────────────────
def compute_synergy(pairs_df: pd.DataFrame, global_baseline: float,
                    group_by_year: bool = True) -> pd.DataFrame:
    """
    Tính co_games, co_wins, synergy_wr (Bayesian), lift theo từng pair.
    group_by_year=True  → group theo (champion_a, champion_b, year)
    group_by_year=False → group chỉ theo (champion_a, champion_b) [all-time]
    """
    group_keys = ["champion_a", "champion_b"]
    if group_by_year:
        group_keys.append("year")

    agg = (
        pairs_df.groupby(group_keys, as_index=False)
        .agg(
            co_games=("is_win", "count"),
            co_wins=("is_win", "sum"),
        )
    )

    # Raw win rate và Bayesian-smoothed synergy win rate
    agg["raw_wr"] = agg["co_wins"] / agg["co_games"]
    agg["synergy_wr"] = (agg["co_wins"] + ALPHA) / (agg["co_games"] + 2 * ALPHA)

    # Lift so với baseline T1 win rate (lift > 1 = synergy dương)
    agg["lift"] = agg["synergy_wr"] / global_baseline

    return agg


# ─── Thêm champion type metadata ──────────────────────────────────────────────
def add_champion_metadata(df: pd.DataFrame, champ_type_map: dict[str, str]) -> pd.DataFrame:
    """Join type cho champion_a và champion_b, tính is_cross_lane."""
    df = df.copy()
    df["type_a"] = df["champion_a"].map(champ_type_map).fillna("unknown")
    df["type_b"] = df["champion_b"].map(champ_type_map).fillna("unknown")

    # Cross-lane = 2 champion khác loại (ví dụ: carry + tank)
    df["is_cross_lane"] = (df["type_a"] != df["type_b"])
    return df


# ─── Filter và sort ───────────────────────────────────────────────────────────
def filter_and_sort(df: pd.DataFrame, min_games: int = MIN_GAMES) -> pd.DataFrame:
    """Chỉ giữ pairs đủ dữ liệu, sort theo lift DESC."""
    filtered = df[df["co_games"] >= min_games].copy()
    filtered = filtered.sort_values("lift", ascending=False).reset_index(drop=True)
    return filtered


# ─── In summary ra console ────────────────────────────────────────────────────
def print_summary(
    by_year_df: pd.DataFrame,
    alltime_df: pd.DataFrame,
    by_year_raw: pd.DataFrame,
    alltime_raw: pd.DataFrame,
    global_baseline: float,
) -> None:
    """In các thống kê tổng quan ra console."""
    sep = "─" * 60

    print(f"\n{sep}")
    print("  CHAMPION SYNERGY NETWORK — SUMMARY")
    print(sep)

    # Global baseline
    print(f"\n  ► Global T1 baseline win rate: {global_baseline:.1%}")

    # Pair counts
    print(f"\n  ► Unique pairs (all-time, trước filter): {len(alltime_raw):,}")
    print(f"  ► Unique pairs (all-time, sau filter ≥{MIN_GAMES} games): {len(alltime_df):,}")
    print(f"  ► Unique pairs (by-year, trước filter): {len(by_year_raw):,}")
    print(f"  ► Unique pairs (by-year, sau filter ≥{MIN_GAMES} games): {len(by_year_df):,}")

    # Top 15 synergy (all-time)
    print(f"\n{sep}")
    print("  TOP 15 SYNERGY PAIRS (all-time, lift DESC)")
    print(sep)
    top_synergy = alltime_df.head(15)[
        ["champion_a", "champion_b", "co_games", "co_wins", "synergy_wr", "lift"]
    ]
    top_synergy = top_synergy.copy()
    top_synergy["synergy_wr"] = top_synergy["synergy_wr"].map("{:.1%}".format)
    top_synergy["lift"] = top_synergy["lift"].map("{:.3f}".format)
    print(top_synergy.to_string(index=False))

    # Bottom 15 anti-synergy (all-time)
    print(f"\n{sep}")
    print("  TOP 15 ANTI-SYNERGY PAIRS (all-time, lift ASC)")
    print(sep)
    anti_synergy = alltime_df.tail(15).sort_values("lift")[
        ["champion_a", "champion_b", "co_games", "co_wins", "synergy_wr", "lift"]
    ]
    anti_synergy = anti_synergy.copy()
    anti_synergy["synergy_wr"] = anti_synergy["synergy_wr"].map("{:.1%}".format)
    anti_synergy["lift"] = anti_synergy["lift"].map("{:.3f}".format)
    print(anti_synergy.to_string(index=False))

    # Breakdown theo year
    print(f"\n{sep}")
    print("  BREAKDOWN THEO NĂM (by-year, sau filter)")
    print(sep)
    year_breakdown = (
        by_year_df.groupby("year")
        .agg(
            pairs=("champion_a", "count"),
            avg_lift=("lift", "mean"),
            max_lift=("lift", "max"),
        )
        .reset_index()
    )
    year_breakdown["avg_lift"] = year_breakdown["avg_lift"].map("{:.3f}".format)
    year_breakdown["max_lift"] = year_breakdown["max_lift"].map("{:.3f}".format)
    print(year_breakdown.to_string(index=False))

    print(f"\n{sep}")


# ─── Main pipeline ────────────────────────────────────────────────────────────
def run(db_url: str = DB_URL, min_games: int = MIN_GAMES) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Chạy toàn bộ pipeline synergy network.
    Returns: (by_year_df, alltime_df)
    """
    print("\n[Model 4] Champion Synergy Network")
    print("─" * 60)

    # Bước 1: Load data
    print("\n[1/6] Loading raw data từ database...")
    df = load_raw_data(db_url)
    t1_df = df[df["team_name"] == "T1"].copy()
    print(f"  T1 rows: {len(t1_df):,} | Games: {t1_df['id_game'].nunique():,}")

    # Load champion type mapping
    champ_type_map = load_champion_types()
    print(f"  Champion types loaded: {len(champ_type_map):,} champions")

    # Bước 2: Tính global baseline win rate của T1
    print("\n[2/6] Tính global T1 baseline win rate...")
    # Dùng 1 row per game (is_win giống nhau cho cả 5 players trong game)
    game_results = t1_df.groupby("id_game")["is_win"].first()
    total_games = len(game_results)
    total_wins = game_results.sum()
    global_baseline = total_wins / total_games
    print(f"  {total_wins}/{total_games} games won → baseline = {global_baseline:.4f} ({global_baseline:.1%})")

    # Bước 3: Generate champion pairs
    print("\n[3/6] Generating champion pairs...")
    pairs_df = generate_pairs(t1_df)

    # Bước 4: Tính synergy stats (by-year và all-time)
    print("\n[4/6] Tính synergy stats...")
    by_year_raw = compute_synergy(pairs_df, global_baseline, group_by_year=True)
    alltime_raw = compute_synergy(pairs_df, global_baseline, group_by_year=False)
    print(f"  Raw by-year pairs: {len(by_year_raw):,}")
    print(f"  Raw all-time pairs: {len(alltime_raw):,}")

    # Bước 5: Thêm champion type metadata
    print("\n[5/6] Thêm champion type metadata...")
    by_year_raw = add_champion_metadata(by_year_raw, champ_type_map)
    alltime_raw = add_champion_metadata(alltime_raw, champ_type_map)

    # Filter và sort
    by_year_df = filter_and_sort(by_year_raw, min_games)
    alltime_df = filter_and_sort(alltime_raw, min_games)
    print(f"  By-year sau filter (≥{min_games} games): {len(by_year_df):,} pairs")
    print(f"  All-time sau filter (≥{min_games} games): {len(alltime_df):,} pairs")

    # Bước 6: In summary
    print("\n[6/6] Summary:")
    print_summary(by_year_df, alltime_df, by_year_raw, alltime_raw, global_baseline)

    # Save output
    OUTPUT_BY_YEAR.parent.mkdir(parents=True, exist_ok=True)
    by_year_df.to_parquet(OUTPUT_BY_YEAR, index=False)
    alltime_df.to_parquet(OUTPUT_ALLTIME, index=False)
    print(f"\n  ✓ Saved: {OUTPUT_BY_YEAR}")
    print(f"  ✓ Saved: {OUTPUT_ALLTIME}")

    return by_year_df, alltime_df


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model 4: Champion Synergy Network")
    parser.add_argument(
        "--min-games",
        type=int,
        default=MIN_GAMES,
        help=f"Threshold tối thiểu co_games để giữ pair (default: {MIN_GAMES})",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=DB_URL,
        help="Database URL (default: dùng DB_URL từ features.py)",
    )
    args = parser.parse_args()

    run(db_url=args.db_url, min_games=args.min_games)
