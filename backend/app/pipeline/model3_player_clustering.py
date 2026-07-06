import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.pipeline.features import DB_URL, load_raw_data

DEFAULT_MIN_GAMES = 25
DEFAULT_PCA_COMPONENTS = 2
DEFAULT_SCALER = "robust"
DEFAULT_FEATURE_SET = "base_years_champs"


def build_player_feature_matrix(df: pd.DataFrame, min_games: int = DEFAULT_MIN_GAMES) -> tuple[pd.DataFrame, list[str]]:
    """Xây dựng feature matrix cho từng player T1."""
    t1_df = df[df["team_id"] == 1].copy()
    if t1_df.empty:
        raise ValueError("No T1 games found in the dataset")

    t1_df = t1_df.sort_values("date_played").copy()
    t1_df["year"] = t1_df["date_played"].dt.year

    # Load champion type mapping từ file JSON
    champion_types_path = BACKEND_ROOT / "data" / "champion_types.json"
    if not champion_types_path.exists():
        champion_types_path = BACKEND_ROOT / "data" / "champions" / "champion_types.json"

    champion_type_map: dict[str, str] = {}
    if champion_types_path.exists():
        champion_type_map = json.loads(champion_types_path.read_text(encoding="utf-8"))

    champion_type_names = [
        "tank_engage",
        "carry_damage",
        "utility_support",
        "assassin_skirmisher",
        "poke_control",
    ]

    records = []
    year_cols = [f"wr_{year}" for year in range(2020, 2026)]

    for player_id, group in t1_df.groupby("player_id", sort=True):
        total_games = len(group)
        if total_games < min_games:
            continue

        wins = int(group["is_win"].sum())
        blue_games = group[group["side"] == "Blue"]
        red_games = group[group["side"] == "Red"]

        # Win rate theo từng năm
        year_wr = {}
        for year_col in year_cols:
            year = int(year_col.split("_")[-1])
            year_group = group[group["year"] == year]
            year_wr[year_col] = (
                round(float(year_group["is_win"].mean()), 4) if not year_group.empty else 0.0
            )

        # Champion stats cơ bản
        champ_stats = (
            group.groupby("champion_name", sort=False)
            .agg(games=("id_game", "count"), wins=("is_win", "sum"))
            .reset_index()
        )
        champ_stats["winrate"] = champ_stats["wins"] / champ_stats["games"]
        champ_stats = champ_stats.sort_values(
            ["games", "winrate"], ascending=[False, False]
        ).reset_index(drop=True)

        # Top champion win rate rank
        champ_wr_list = champ_stats["winrate"].head(10).tolist()
        top10_features = {
            f"champ_wr_rank{idx}": champ_wr_list[idx - 1] if idx - 1 < len(champ_wr_list) else 0.0
            for idx in range(1, 11)
        }

        # Champion type distribution
        type_counts = {type_name: 0 for type_name in champion_type_names}
        known_picks = 0
        for _, row in champ_stats.iterrows():
            champion_name = row["champion_name"]
            champion_type = champion_type_map.get(champion_name)
            if champion_type is None:
                continue
            picks = int(row["games"])
            known_picks += picks
            if champion_type in type_counts:
                type_counts[champion_type] += picks

        type_pct_features = {
            f"pct_{type_name}": round(type_counts[type_name] / known_picks, 4) if known_picks else 0.0
            for type_name in champion_type_names
        }

        # Herfindahl index trên top 20 champion
        top20_champs = champ_stats.head(20).copy()
        if not top20_champs.empty and total_games > 0:
            hhi = float(((top20_champs["games"] / total_games) ** 2).sum())
        else:
            hhi = 0.0

        # Position mode one-hot
        position_mode = (
            group["position"].fillna("").astype(str).str.strip().str.upper()
            .replace({"JUNGLE": "JUNGLER", "BOTTOM": "BOT", "BOT": "BOT"})
            .mode()
        )
        mode_position = position_mode.iloc[0] if not position_mode.empty else "UNKNOWN"
        position_features = {
            "pos_TOP": 1.0 if mode_position == "TOP" else 0.0,
            "pos_JUNGLER": 1.0 if mode_position == "JUNGLER" else 0.0,
            "pos_MID": 1.0 if mode_position == "MID" else 0.0,
            "pos_ADC": 1.0 if mode_position == "ADC" else 0.0,
            "pos_SUPPORT": 1.0 if mode_position == "SUPPORT" else 0.0,
            "pos_BOT": 1.0 if mode_position == "BOT" else 0.0,
        }

        # Career features
        valid_years = []
        for year in range(2020, 2026):
            year_group = group[group["year"] == year]
            if not year_group.empty:
                valid_years.append((year, round(float(year_group["is_win"].mean()), 4)))

        career_peak_wr = round(max([wr for _, wr in valid_years], default=0.0), 4)
        if len(valid_years) >= 2:
            career_trend = round(valid_years[-1][1] - valid_years[0][1], 4)
        else:
            career_trend = 0.0
        is_active_2025 = 1 if any(year == 2025 for year, _ in valid_years) else 0

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
            **type_pct_features,
            "hhi_top20": round(hhi, 4),
            **position_features,
            "career_peak_wr": career_peak_wr,
            "career_trend": round(career_trend, 4),
            "is_active_2025": int(is_active_2025),
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
        *[f"pct_{type_name}" for type_name in champion_type_names],
        "hhi_top20",
        "pos_TOP",
        "pos_JUNGLER",
        "pos_MID",
        "pos_ADC",
        "pos_SUPPORT",
        "pos_BOT",
        "career_peak_wr",
        "career_trend",
        "is_active_2025",
        "champ_pool_size",
        "avg_games_per_champ",
    ]
    feature_df = feature_df[["player_id", "player_name", *feature_cols]]
    return feature_df, feature_cols


def run_clustering(
    df: pd.DataFrame,
    feature_cols: list[str],
    k: int = 3,
    min_games: int = DEFAULT_MIN_GAMES,
    pca_components: int = DEFAULT_PCA_COMPONENTS,
    scaler_name: str = DEFAULT_SCALER,
) -> tuple[pd.DataFrame, dict]:
    """Scale features, giảm chiều bằng PCA rồi chạy KMeans."""
    feature_matrix = df[feature_cols].fillna(0).astype(float).copy()

    scaler_map = {
        "standard": StandardScaler(),
        "robust": RobustScaler(),
        "minmax": MinMaxScaler(),
    }
    if scaler_name not in scaler_map:
        raise ValueError(f"Unsupported scaler: {scaler_name}")

    scaler = scaler_map[scaler_name]
    scaled_features = scaler.fit_transform(feature_matrix)
    scaled_df = pd.DataFrame(scaled_features, columns=feature_cols, index=df.index)

    pca = PCA(n_components=pca_components, random_state=42)
    pca_components_matrix = pca.fit_transform(scaled_df)
    pca_df = pd.DataFrame(pca_components_matrix, columns=[f"PC{idx}" for idx in range(1, pca_components + 1)], index=df.index)

    inertias = []
    for cluster_k in range(2, 9):
        model = KMeans(n_clusters=cluster_k, random_state=42, n_init=10)
        model.fit(pca_df)
        inertias.append((cluster_k, float(model.inertia_)))

    inertia_df = pd.DataFrame(inertias, columns=["k", "inertia"])
    print("\nElbow Method")
    print(inertia_df.to_string(index=False))

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(pca_df)
    silhouette = silhouette_score(pca_df, clusters)

    result_df = df.copy()
    result_df["cluster"] = clusters
    for col in pca_df.columns:
        result_df[col] = pca_df[col].values

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
        "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "pca_n_components": pca_components,
        "scaler": scaler_name,
    }
    return result_df, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Player clustering for T1 performance analytics")
    parser.add_argument("--k", type=int, default=3, help="Số cluster cho KMeans")
    parser.add_argument("--min-games", type=int, default=DEFAULT_MIN_GAMES, help="Ngưỡng tối thiểu games")
    parser.add_argument("--db-url", default=DB_URL, help="Database URL")
    parser.add_argument("--scaler", choices=["standard", "robust", "minmax"], default=DEFAULT_SCALER, help="Phương pháp scaling")
    parser.add_argument("--pca-components", type=int, default=DEFAULT_PCA_COMPONENTS, help="Số thành phần PCA")
    args = parser.parse_args()

    print("Đang tải dữ liệu từ database...")
    df = load_raw_data(args.db_url)
    print(f"Đã load {len(df)} rows")

    print("Đang xây dựng feature matrix...")
    feature_df, feature_cols = build_player_feature_matrix(df, min_games=args.min_games)
    print(f"Số player sau lọc: {len(feature_df)}")
    print("Feature cols:")
    print(feature_cols)

    print("Đang chạy clustering...")
    result_df, metrics = run_clustering(
        feature_df,
        feature_cols,
        k=args.k,
        min_games=args.min_games,
        pca_components=args.pca_components,
        scaler_name=args.scaler,
    )

    output_path = BACKEND_ROOT / "data" / "model3_clusters.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_parquet(output_path, index=False)

    print(f"\nSaved to {output_path}")
    print(f"Silhouette Score: {metrics['silhouette_score']:.4f}")
    print(f"Scaler: {metrics['scaler']}")
    print(f"PCA components: {metrics['pca_n_components']}")
    print(f"PCA explained variance ratio: {metrics['pca_explained_variance_ratio']}")
    print("\nCluster summary:")
    print(metrics["summary"].to_string(index=False))

    print("\nFeature importance by cluster:")
    cluster_feature_means = result_df.groupby("cluster")[feature_cols].mean()
    for cluster_id in sorted(cluster_feature_means.index):
        top_features = cluster_feature_means.loc[cluster_id].sort_values(ascending=False).head(3)
        print(f"Cluster {cluster_id}: {', '.join([f'{name}={value:.4f}' for name, value in top_features.items()])}")

    print("\nPreview:")
    print(result_df[["player_name", "cluster", "PC1", "PC2", "overall_winrate", "total_games"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
