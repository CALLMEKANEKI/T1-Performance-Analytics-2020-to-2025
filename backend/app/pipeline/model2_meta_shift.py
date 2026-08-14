"""
Model 2: Meta shift time series theo champion, bucket 2 tuáº§n.
Cháº¡y tá»« thÆ° má»¥c backend: python -m app/pipeline/model2_meta_shift.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from app.pipeline.features import DB_URL, load_raw_data

BUCKET_DAYS = 14
BACKEND_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = BACKEND_DIR / "data" / "model2_timeseries.parquet"
SHIFT_OUTPUT_PATH = BACKEND_DIR / "data" / "model2_shift_events.parquet"
MERGED_OUTPUT_PATH = BACKEND_DIR / "data" / "model2_merged_events.parquet"

# â”€â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MIN_BASELINE_BUCKETS = 6   # Sá»‘ bucket cáº§n thiáº¿t trÆ°á»›c khi tÃ­nh z-score
MIN_VOLUME = 5             # Tá»•ng pick+ban tá»‘i thiá»ƒu á»Ÿ bucket hiá»‡n táº¡i
MIN_BASELINE_TOTAL = 15    # Tá»•ng volume trong baseline
Z_SCORE_THRESHOLD = 2.0    # NgÆ°á»¡ng composite z-score Ä‘á»ƒ cÃ´ng nháº­n shift event


def load_ban_data(db_url: str = DB_URL) -> pd.DataFrame:
    """Láº¥y ban theo game + champion (meta presence, khÃ´ng riÃªng T1)."""
    engine = create_engine(db_url)
    query = text("""
        SELECT
            g.id_game,
            g.date_played,
            b.champion_id
        FROM bans b
        JOIN games g ON b.game_id = g.id_game
        ORDER BY g.date_played, g.id_game
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        bans = pd.DataFrame(result.mappings().all())
    bans["date_played"] = pd.to_datetime(bans["date_played"])
    return bans


def assign_two_week_bucket(dates: pd.Series, origin: pd.Timestamp) -> pd.Series:
    """
    Floor date_played vá» má»‘c 2 tuáº§n, má»‘c báº¯t Ä‘áº§u tá»« ngÃ y nhá» nháº¥t trong data.
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
    Build time series (champion_id, bucket) vá»›i picks, bans, wins, win_rate, presence_rate.
    """
    # Má»‘c bucket chung cho picks vÃ  bans
    min_date = min(picks_df["date_played"].min(), bans_df["date_played"].min())

    picks = picks_df[["id_game", "date_played", "champion_id", "is_win"]].copy()
    picks["bucket"] = assign_two_week_bucket(picks["date_played"], min_date)

    bans = bans_df[["id_game", "date_played", "champion_id"]].copy()
    bans["bucket"] = assign_two_week_bucket(bans["date_played"], min_date)

    # Tá»•ng sá»‘ game trong má»—i bucket (dÃ¹ng cho presence_rate)
    games = picks_df[["id_game", "date_played"]].drop_duplicates()
    games["bucket"] = assign_two_week_bucket(games["date_played"], min_date)
    total_games = (
        games.groupby("bucket", as_index=False)["id_game"]
        .nunique()
        .rename(columns={"id_game": "total_games_in_bucket"})
    )

    # Picks + wins (chá»‰ tá»« draft pick, khÃ´ng tÃ­nh ban)
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

    # Gá»™p picks vÃ  bans (champion cÃ³ thá»ƒ chá»‰ pick hoáº·c chá»‰ ban trong bucket)
    ts = pick_stats.merge(ban_stats, on=["champion_id", "bucket"], how="outer")
    ts["picks"] = ts["picks"].fillna(0).astype(int)
    ts["wins"] = ts["wins"].fillna(0).astype(int)
    ts["bans"] = ts["bans"].fillna(0).astype(int)

    ts = ts.merge(total_games, on="bucket", how="left")

    # Raw win rate vÃ  presence trong meta
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
    """TÃ­nh z-score vÃ  flag cÃ¡c bucket cÃ³ dáº¥u hiá»‡u meta shift."""
    ts = ts.sort_values(["champion_id", "bucket"]).copy()
    ts["z_winrate"] = np.nan
    ts["z_presence"] = np.nan
    ts["composite_score"] = np.nan
    ts["is_shift_event"] = False

    for champion_id, group in ts.groupby("champion_id", sort=False):
        group = group.sort_values("bucket").copy()
        for idx in range(len(group)):
            if idx < MIN_BASELINE_BUCKETS:
                # ChÆ°a Ä‘á»§ baseline 6 bucket trÆ°á»›c => bá» qua early buckets
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
            min_volume = (group.iloc[idx]["picks"] + group.iloc[idx]["bans"]) >= MIN_VOLUME
            baseline_total_volume = (baseline["picks"] + baseline["bans"]).sum()
            has_enough_baseline = baseline_total_volume >= MIN_BASELINE_TOTAL

            is_shift_event = (composite_score > Z_SCORE_THRESHOLD) and min_volume and has_enough_baseline

            ts.loc[group.index[idx], "z_winrate"] = z_winrate
            ts.loc[group.index[idx], "z_presence"] = z_presence
            ts.loc[group.index[idx], "composite_score"] = composite_score
            ts.loc[group.index[idx], "is_shift_event"] = is_shift_event

    return ts.reset_index(drop=True)


def merge_consecutive_events(shift_df: pd.DataFrame) -> pd.DataFrame:
    """Gom cÃ¡c bucket shift liÃªn tiáº¿p thÃ nh 1 event group."""
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


def main() -> None:
    """Build model2 timeseries, detect shifts and write parquet outputs."""
    print("Building Model2 champion timeseries...")
    try:
        picks_df = load_raw_data(DB_URL)
        bans_df = load_ban_data(DB_URL)

        ts = build_champion_timeseries(picks_df, bans_df)
        ts.to_parquet(OUTPUT_PATH, index=False)
        print(f"Wrote timeseries to {OUTPUT_PATH}")

        shift_df = detect_meta_shifts(ts)
        shift_df.to_parquet(SHIFT_OUTPUT_PATH, index=False)
        print(f"Wrote shift events to {SHIFT_OUTPUT_PATH}")

        merged = merge_consecutive_events(shift_df)
        merged.to_parquet(MERGED_OUTPUT_PATH, index=False)
        print(f"Wrote merged events to {MERGED_OUTPUT_PATH}")
    except Exception as exc:
        print("Error building model2 artifacts:", exc)


if __name__ == "__main__":
    main()
