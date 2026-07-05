import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.pipeline.features import DB_URL, load_raw_data


def build_player_feature_matrix(df: pd.DataFrame, min_games: int = 5) -> tuple[pd.DataFrame, list[str]]:
    """Xây dựng feature matrix cho từng player T1."""
    t1_df = df[df["team_id"] == 1].copy()
    if t1_df.empty:
        raise ValueError("No T1 games found in the dataset")

    t1_df = t1_df.sort_values("date_played").copy()
    t1_df["year"] = t1_df["date_played"].dt.year

    records = []
    year_cols = [f"wr_{year}" for year in range(2020, 2026)]

    for player_id, group in t1_df.groupby("player_id", sort=True):
        total_games = len(group)
        if total_games < min_games:
            continue

        wins = int(group["is_win"].sum())
        blue_games = group[group["side"] == "Blue"]
        red_games = group[group["side"] == "Red"]

        year_wr = {}
        for year_col in year_cols:
            year = int(year_col.split("_")[-1])
            year_group = group[group["year"] == year]
            year_wr[year_col] = (
                year_group["is_win"].mean() if not year_group.empty else 0.0
            )

        champ_stats = (
            group.groupby("champion_name", sort=False)
            .agg(games=("id_game", "count"), wins=("is_win", "sum"))
            .reset_index()
        )
        champ_stats["winrate"] = champ_stats["wins"] / champ_stats["games"]
        champ_stats = champ_stats.sort_values(
            ["games", "winrate"], ascending=[False, False]
        ).reset_index(drop=True)

        champ_wr_list = champ_stats["winrate"].head(10).tolist()
        top10_features = {
            f"champ_wr_rank{idx}": champ_wr_list[idx - 1] if idx - 1 < len(champ_wr_list) else 0.0
            for idx in range(1, 11)
        }

        champ_pool_size = int(champ_stats["champion_name"].nunique())
        avg_games_per_champ = total_games / champ_pool_size if champ_pool_size else 0.0

        record = {
            "player_id": player_id,
            "player_name": group["ingame_name"].iloc[0],
            "overall_winrate": round(wins / total_games, 4),
            "total_games": int(total_games),
            "winrate_blue": round(blue_games["is_win"].mean(), 4) if not blue_games.empty else 0.0,
            "winrate_red": round(red_games["is_win"].mean(), 4) if not red_games.empty else 0.0,
            **year_wr,
            **top10_features,
            "champ_pool_size": champ_pool_size,
            "avg_games_per_champ": round(avg_games_per_champ, 4),
        }
        records.append(record)

    if not records:
        raise ValueError("No players met the minimum game requirement")

    feature_df = pd.DataFrame(records)
    feature_cols = [
        "overall_winrate",
        "total_games",
        "winrate_blue",
        "winrate_red",
        *year_cols,
        *[f"champ_wr_rank{idx}" for idx in range(1, 11)],
        "champ_pool_size",
        "avg_games_per_champ",
    ]
    feature_df = feature_df[["player_id", "player_name", *feature_cols]]
    return feature_df, feature_cols


def run_clustering(
    df: pd.DataFrame,
    feature_cols: list[str],
    k: int = 3,
    min_games: int = 5,
) -> tuple[pd.DataFrame, dict]:
    """Scale features, chạy elbow, KMeans, PCA và lưu kết quả."""
    feature_matrix = df[feature_cols].fillna(0).astype(float).copy()

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)
    scaled_df = pd.DataFrame(scaled_features, columns=feature_cols, index=df.index)

    inertias = []
    for cluster_k in range(2, 9):
        model = KMeans(n_clusters=cluster_k, random_state=42, n_init=10)
        model.fit(scaled_df)
        inertias.append((cluster_k, float(model.inertia_)))

    inertia_df = pd.DataFrame(inertias, columns=["k", "inertia"])
    print("\nElbow Method")
    print(inertia_df.to_string(index=False))

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(scaled_df)
    silhouette = silhouette_score(scaled_df, clusters)

    pca = PCA(n_components=2, random_state=42)
    pca_components = pca.fit_transform(scaled_df)

    result_df = df.copy()
    result_df = result_df.rename(columns={"player_name": "player_name"})
    result_df["cluster"] = clusters
    result_df["PC1"] = pca_components[:, 0]
    result_df["PC2"] = pca_components[:, 1]

    summary = (
        result_df.groupby("cluster")
        .agg(
            player_count=("player_id", "count"),
            avg_winrate=("overall_winrate", "mean"),
            avg_games=("total_games", "mean"),
            players=("player_name", lambda s: ", ".join(s.astype(str))),
        )
        .reset_index()
    )

    metrics = {
        "k": k,
        "silhouette_score": float(silhouette),
        "inertia_table": inertia_df,
        "summary": summary,
        "min_games": min_games,
    }
    return result_df, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Player clustering for T1 performance analytics")
    parser.add_argument("--k", type=int, default=3, help="Số cluster cho KMeans")
    parser.add_argument("--min-games", type=int, default=5, help="Ngưỡng tối thiểu games")
    parser.add_argument("--db-url", default=DB_URL, help="Database URL")
    args = parser.parse_args()

    print("Đang tải dữ liệu từ database...")
    df = load_raw_data(args.db_url)
    print(f"Đã load {len(df)} rows")

    print("Đang xây dựng feature matrix...")
    feature_df, feature_cols = build_player_feature_matrix(df, min_games=args.min_games)
    print(f"Số player sau lọc: {len(feature_df)}")

    print("Đang chạy clustering...")
    result_df, metrics = run_clustering(feature_df, feature_cols, k=args.k, min_games=args.min_games)

    output_path = Path(__file__).resolve().parents[2] / "data" / "model3_clusters.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_parquet(output_path, index=False)

    print(f"\nSaved to {output_path}")
    print(f"Silhouette Score: {metrics['silhouette_score']:.4f}")
    print("\nCluster summary:")
    print(metrics["summary"].to_string(index=False))

    print("\nPreview:")
    print(result_df[["player_name", "cluster", "PC1", "PC2", "overall_winrate", "total_games"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
