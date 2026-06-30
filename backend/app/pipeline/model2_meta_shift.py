"""
Model 2: Meta shift time series theo champion, bucket 2 tuần.
Chạy từ thư mục backend: python app/pipeline/model2_meta_shift.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from features import DB_URL, load_raw_data

BUCKET_DAYS = 14
BACKEND_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = BACKEND_DIR / "data" / "model2_timeseries.parquet"
SHIFT_OUTPUT_PATH = BACKEND_DIR / "data" / "model2_shift_events.parquet"
MERGED_OUTPUT_PATH = BACKEND_DIR / "data" / "model2_merged_events.parquet"


def load_ban_data(db_url: str = DB_URL) -> pd.DataFrame:
    """Lấy ban theo game + champion (meta presence, không riêng T1)."""
    engine = create_engine(db_url)
    query = """
        SELECT
            g.id_game,
            g.date_played,
            b.champion_id
        FROM bans b
        JOIN games g ON b.game_id = g.id_game
        ORDER BY g.date_played, g.id_game
    """
    bans = pd.read_sql(query, engine)
    bans["date_played"] = pd.to_datetime(bans["date_played"])
    return bans


def assign_two_week_bucket(dates: pd.Series, origin: pd.Timestamp) -> pd.Series:
    """
    Floor date_played về mốc 2 tuần, mốc bắt đầu từ ngày nhỏ nhất trong data.
    """
    origin = origin.normalize()
    days_since = (dates - origin).dt.days
    bucket_offset = (days_since // BUCKET_DAYS) * BUCKET_DAYS
    return origin + pd.to_timedelta(bucket_offset, unit="D")


def build_champion_timeseries(
    picks_df: pd.DataFrame,
    bans_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build time series (champion_id, bucket) với picks, bans, wins, win_rate, presence_rate.
    """
    # Mốc bucket chung cho picks và bans
    min_date = min(picks_df["date_played"].min(), bans_df["date_played"].min())

    picks = picks_df[["id_game", "date_played", "champion_id", "is_win"]].copy()
    picks["bucket"] = assign_two_week_bucket(picks["date_played"], min_date)

    bans = bans_df[["id_game", "date_played", "champion_id"]].copy()
    bans["bucket"] = assign_two_week_bucket(bans["date_played"], min_date)

    # Tổng số game trong mỗi bucket (dùng cho presence_rate)
    games = picks_df[["id_game", "date_played"]].drop_duplicates()
    games["bucket"] = assign_two_week_bucket(games["date_played"], min_date)
    total_games = (
        games.groupby("bucket", as_index=False)["id_game"]
        .nunique()
        .rename(columns={"id_game": "total_games_in_bucket"})
    )

    # Picks + wins (chỉ từ draft pick, không tính ban)
    pick_stats = (
        picks.groupby(["champion_id", "bucket"], as_index=False)
        .agg(picks=("is_win", "count"), wins=("is_win", "sum"))
    )

    # Bans theo champion + bucket
    ban_stats = (
        bans.groupby(["champion_id", "bucket"], as_index=False)
        .size()
        .rename(columns={"size": "bans"})
    )

    # Gộp picks và bans (champion có thể chỉ pick hoặc chỉ ban trong bucket)
    ts = pick_stats.merge(ban_stats, on=["champion_id", "bucket"], how="outer")
    ts["picks"] = ts["picks"].fillna(0).astype(int)
    ts["wins"] = ts["wins"].fillna(0).astype(int)
    ts["bans"] = ts["bans"].fillna(0).astype(int)

    ts = ts.merge(total_games, on="bucket", how="left")

    # Raw win rate và presence trong meta
    ts["win_rate"] = ts.apply(
        lambda r: r["wins"] / r["picks"] if r["picks"] > 0 else float("nan"),
        axis=1,
    )
    ts["presence_rate"] = (ts["picks"] + ts["bans"]) / (ts["total_games_in_bucket"] * 2)

    ts = ts.sort_values(["champion_id", "bucket"]).reset_index(drop=True)
    return ts[
        [
            "champion_id",
            "bucket",
            "picks",
            "bans",
            "wins",
            "win_rate",
            "presence_rate",
            "total_games_in_bucket",
        ]
    ]


def detect_meta_shifts(ts: pd.DataFrame) -> pd.DataFrame:
    """Tính z-score và flag các bucket có dấu hiệu meta shift."""
    ts = ts.sort_values(["champion_id", "bucket"]).copy()
    ts["z_winrate"] = np.nan
    ts["z_presence"] = np.nan
    ts["composite_score"] = np.nan
    ts["is_shift_event"] = False

    for champion_id, group in ts.groupby("champion_id", sort=False):
        group = group.sort_values("bucket").copy()
        for idx in range(len(group)):
            if idx < 6:
                # Chưa đủ baseline 6 bucket trước => bỏ qua early buckets
                continue

            baseline = group.iloc[idx - 6 : idx]
            baseline_mean_winrate = baseline["win_rate"].mean()
            baseline_std_winrate = baseline["win_rate"].std(ddof=0)
            baseline_mean_presence = baseline["presence_rate"].mean()
            baseline_std_presence = baseline["presence_rate"].std(ddof=0)

            current_winrate = group.iloc[idx]["win_rate"]
            current_presence = group.iloc[idx]["presence_rate"]

            if pd.isna(current_winrate):
                z_winrate = 0.0
            elif pd.isna(baseline_std_winrate) or baseline_std_winrate == 0:
                z_winrate = 0.0
            else:
                z_winrate = (current_winrate - baseline_mean_winrate) / baseline_std_winrate

            if pd.isna(baseline_std_presence) or baseline_std_presence == 0:
                z_presence = 0.0
            else:
                z_presence = (current_presence - baseline_mean_presence) / baseline_std_presence

            composite_score = float(np.sqrt(z_winrate**2 + z_presence**2))
            min_volume = (group.iloc[idx]["picks"] + group.iloc[idx]["bans"]) >= 5
            baseline_total_volume = (baseline["picks"] + baseline["bans"]).sum()
            has_enough_baseline = baseline_total_volume >= 15

            is_shift_event = (composite_score > 2.0) and min_volume and has_enough_baseline

            ts.loc[group.index[idx], "z_winrate"] = z_winrate
            ts.loc[group.index[idx], "z_presence"] = z_presence
            ts.loc[group.index[idx], "composite_score"] = composite_score
            ts.loc[group.index[idx], "is_shift_event"] = is_shift_event

    return ts.reset_index(drop=True)


def merge_consecutive_events(shift_df: pd.DataFrame) -> pd.DataFrame:
    """Gom các bucket shift liên tiếp thành 1 event group."""
    event_df = shift_df[shift_df["is_shift_event"]].copy()
    if event_df.empty:
        return pd.DataFrame(
            columns=[
                "champion_id",
                "start_bucket",
                "end_bucket",
                "duration_buckets",
                "total_picks",
                "total_bans",
                "avg_win_rate",
                "max_composite_score",
                "peak_bucket",
            ]
        )

    results = []
    for champion_id, group in event_df.groupby("champion_id", sort=False):
        group = group.sort_values("bucket").copy()
        group["gap_days"] = (group["bucket"] - group["bucket"].shift(1)).dt.days
        group["group_id"] = (group["gap_days"].ne(14) | group["gap_days"].isna()).cumsum()

        for _, event_group in group.groupby("group_id", sort=False):
            peak_idx = event_group["composite_score"].idxmax()
            peak_row = event_group.loc[peak_idx]
            results.append(
                {
                    "champion_id": champion_id,
                    "start_bucket": event_group["bucket"].min(),
                    "end_bucket": event_group["bucket"].max(),
                    "duration_buckets": len(event_group),
                    "total_picks": int(event_group["picks"].sum()),
                    "total_bans": int(event_group["bans"].sum()),
                    "avg_win_rate": float(event_group["win_rate"].mean()),
                    "max_composite_score": float(peak_row["composite_score"]),
                    "peak_bucket": peak_row["bucket"],
                }
            )

    merged_df = pd.DataFrame(results)
    if merged_df.empty:
        return merged_df

    return merged_df.sort_values("max_composite_score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    print("Loading pick data...")
    picks_df = load_raw_data()
    print(f"  {len(picks_df)} pick rows, {picks_df['id_game'].nunique()} games")

    print("Loading ban data...")
    bans_df = load_ban_data()
    print(f"  {len(bans_df)} ban rows")

    print("\nBuilding champion meta time series (2-week buckets)...")
    ts = build_champion_timeseries(picks_df, bans_df)

    print("\nDetecting meta shifts...")
    shift_df = detect_meta_shifts(ts)
    merged_events = merge_consecutive_events(shift_df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHIFT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MERGED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts.to_parquet(OUTPUT_PATH, index=False)
    shift_df.to_parquet(SHIFT_OUTPUT_PATH, index=False)
    merged_events.to_parquet(MERGED_OUTPUT_PATH, index=False)
    print(f"Saved time series to {OUTPUT_PATH}")
    print(f"Saved shift events to {SHIFT_OUTPUT_PATH}")
    print(f"Saved merged events to {MERGED_OUTPUT_PATH}")
    print(f"Shape: {ts.shape}")

    shift_events = shift_df[shift_df["is_shift_event"]].copy()
    print(f"\nTong so shift events detect duoc: {len(shift_events)}")
    print(f"Tong so merged events: {len(merged_events)} (so voi 302 events goc)")

    if not shift_events.empty:
        engine = create_engine(DB_URL)
        champion_names = pd.read_sql_query(
            "SELECT id_champion, name FROM champions",
            engine,
        )
        champion_names = champion_names.rename(
            columns={"id_champion": "champion_id", "name": "champion_name"}
        )
        top_shift_events = (
            shift_events.sort_values("composite_score", ascending=False)
            .head(15)
            .merge(champion_names, on="champion_id", how="left")
        )
        print("\nTop 15 shift events:")
        print(
            top_shift_events[
                [
                    "champion_name",
                    "champion_id",
                    "bucket",
                    "win_rate",
                    "presence_rate",
                    "composite_score",
                ]
            ].to_string(index=False)
        )

    if not merged_events.empty:
        merged_with_names = merged_events.merge(champion_names, on="champion_id", how="left")
        print("\nTop 15 merged events:")
        print(
            merged_with_names[
                [
                    "champion_name",
                    "champion_id",
                    "start_bucket",
                    "end_bucket",
                    "duration_buckets",
                    "max_composite_score",
                    "peak_bucket",
                ]
            ].head(15).to_string(index=False)
        )

    n_buckets = ts["bucket"].nunique()
    print(f"\nTong so bucket (2-week periods): {n_buckets}")

    # Top 5 champion presence cao nhất (trung bình qua các bucket có xuất hiện)
    top_presence = (
        ts.groupby("champion_id", as_index=False)["presence_rate"]
        .mean()
        .sort_values("presence_rate", ascending=False)
        .head(5)
    )
    print("\nTop 5 champion co presence_rate trung binh cao nhat:")
    print(top_presence.to_string(index=False))

    # Time series champion id=14 (pick nhieu nhat)
    champ_id = 14
    champ_ts = ts[ts["champion_id"] == champ_id].copy()
    print(f"\nTime series day du champion_id={champ_id} ({len(champ_ts)} buckets):")
    print(champ_ts.to_string(index=False))
    
