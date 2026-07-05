"""
Model 3: Player Clustering (KMeans)
Build feature vectors for each T1 player, cluster them into groups based on performance patterns.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import logging
from app.pipeline.features import DB_URL, load_raw_data  # assume these exist
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = BACKEND_DIR / "data" / "model3_clusters.parquet"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def get_player_features(engine):
    """
    Build feature matrix for all players who have ever played for T1 (team_id=1).
    Returns DataFrame with player_id, ingame_name, and all features.
    """
    # Query to get all T1 players (unique)
    query_players = text("""
        SELECT DISTINCT p.id_player, p.ingame_name
        FROM players p
        JOIN game_players gp ON p.id_player = gp.player_id
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        WHERE gt.team_id = 1
    """)
    players = pd.read_sql(query_players, engine)

    if players.empty:
        log.warning("No T1 players found in database.")
        return pd.DataFrame()

    # For each player, we need to compute the features.
    # We'll do this in a single query using window functions or aggregation.

    # Feature 1: overall winrate & total games
    query_stats = text("""
        SELECT
            gp.player_id,
            COUNT(*) AS total_games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) AS total_wins
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        WHERE gt.team_id = 1
        GROUP BY gp.player_id
    """)
    stats = pd.read_sql(query_stats, engine)
    stats['overall_winrate'] = stats['total_wins'] / stats['total_games']

    # Merge with players
    df = players.merge(stats, on='player_id', how='left')
    # Ensure numeric columns
    df['total_games'] = df['total_games'].fillna(0).astype(int)
    df['overall_winrate'] = df['overall_winrate'].fillna(0)

    # Feature 2: winrate by side (Blue/Red)
    query_side = text("""
        SELECT
            gp.player_id,
            gt.side,
            COUNT(*) AS games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) AS wins
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        WHERE gt.team_id = 1
        GROUP BY gp.player_id, gt.side
    """)
    side_stats = pd.read_sql(query_side, engine)
    # Pivot to get blue and red winrates
    # Pivot games và wins riêng, rồi merge
    games_pivot = side_stats.pivot(index='player_id', columns='side', values='games').fillna(0)
    wins_pivot  = side_stats.pivot(index='player_id', columns='side', values='wins').fillna(0)

    side_pivot = pd.DataFrame(index=games_pivot.index)
    side_pivot['blue_games'] = games_pivot.get('Blue', 0)
    side_pivot['red_games']  = games_pivot.get('Red', 0)
    side_pivot['blue_wins']  = wins_pivot.get('Blue', 0)
    side_pivot['red_wins']   = wins_pivot.get('Red', 0)
    side_pivot['winrate_blue'] = (side_pivot['blue_wins'] / side_pivot['blue_games'].replace(0, np.nan)).fillna(0)
    side_pivot['winrate_red']  = (side_pivot['red_wins']  / side_pivot['red_games'].replace(0, np.nan)).fillna(0)

    side_pivot['winrate_blue'] = side_pivot['blue_wins'] / side_pivot['blue_games'].replace(0, np.nan)
    side_pivot['winrate_red'] = side_pivot['red_wins'] / side_pivot['red_games'].replace(0, np.nan)
    side_pivot[['winrate_blue', 'winrate_red']] = side_pivot[['winrate_blue', 'winrate_red']].fillna(0)
    df = df.merge(side_pivot[['winrate_blue', 'winrate_red']], on='player_id', how='left').fillna(0)

    # Feature 3: winrate by year (2020-2025)
    years = list(range(2020, 2026))
    query_year = text("""
        SELECT
            gp.player_id,
            EXTRACT(YEAR FROM g.date_played) AS year,
            COUNT(*) AS games,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) AS wins
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        JOIN games g ON gt.game_id = g.id_game
        WHERE gt.team_id = 1
        GROUP BY gp.player_id, year
    """)
    year_stats = pd.read_sql(query_year, engine)
    # Pivot to get winrate per year
    year_pivot = year_stats.pivot(index='player_id', columns='year', values=['games', 'wins']).fillna(0)
    # Compute winrates for each year, fill missing with 0
    for y in years:
        if y in year_pivot.columns.get_level_values(1):
            games = year_pivot['games', y]
            wins = year_pivot['wins', y]
            wr = wins / games.replace(0, np.nan)
            df[f'wr_{y}'] = wr.fillna(0)
        else:
            df[f'wr_{y}'] = 0

    # Feature 4: top 10 champions win rate
    # We need per player per champion picks and wins, then rank by picks.
    query_champ = text("""
        SELECT
            gp.player_id,
            gp.champion_id,
            c.name AS champion_name,
            COUNT(*) AS picks,
            SUM(CASE WHEN gt.result = 'WIN' THEN 1 ELSE 0 END) AS wins
        FROM game_players gp
        JOIN game_teams gt ON gp.game_team_id = gt.id_game_team
        JOIN champions c ON gp.champion_id = c.id_champion
        WHERE gt.team_id = 1
        GROUP BY gp.player_id, gp.champion_id, c.name
    """)
    champ_stats = pd.read_sql(query_champ, engine)
    # For each player, get top 10 champions by picks
    champ_stats['rank'] = champ_stats.groupby('player_id')['picks'].rank(method='dense', ascending=False)
    top10 = champ_stats[champ_stats['rank'] <= 10].copy()
    # Compute winrate per champion (wins/picks)
    top10['winrate'] = top10['wins'] / top10['picks']
    # Pivot to have columns champ_wr_rank1..champ_wr_rank10
    top10_pivot = top10.pivot(index='player_id', columns='rank', values='winrate').fillna(0)
    # Rename columns
    top10_pivot.columns = [f'champ_wr_rank{int(c)}' for c in top10_pivot.columns]
    # Ensure all 10 columns exist
    for i in range(1, 11):
        col = f'champ_wr_rank{i}'
        if col not in top10_pivot.columns:
            top10_pivot[col] = 0
    df = df.merge(top10_pivot, on='player_id', how='left').fillna(0)

    # Feature 5: champion pool size
    champ_pool = champ_stats.groupby('player_id')['champion_id'].nunique().reset_index(name='champ_pool_size')
    df = df.merge(champ_pool, on='player_id', how='left').fillna(0)

    # Feature 6: avg games per champion
    df['avg_games_per_champ'] = df['total_games'] / df['champ_pool_size'].replace(0, np.nan)
    df['avg_games_per_champ'] = df['avg_games_per_champ'].fillna(0)

    return df


def run_clustering(K=3):
    """
    Main clustering pipeline.
    Default K=3, but can be overridden.
    """
    engine = create_engine(DB_URL)
    log.info("Loading raw data... (using engine)")
    # We don't actually need load_raw_data if we query directly.
    # But we keep the import for compatibility.

    # Get feature matrix
    df = get_player_features(engine)

    if df.empty:
        log.error("No data to cluster.")
        return

    # Filter players with at least 5 games
    df_filtered = df[df['total_games'] >= 5].copy()
    if len(df_filtered) < K:
        log.warning(f"Only {len(df_filtered)} players, cannot cluster with K={K}. Set K=2.")
        K = min(K, len(df_filtered))

    # Separate identifiers and features
    identifiers = df_filtered[['player_id', 'ingame_name']]
    feature_cols = [col for col in df_filtered.columns if col not in ['player_id', 'ingame_name']]
    X = df_filtered[feature_cols].copy()

    # Step 2: Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Step 3: Elbow (optional, we'll just use K=3 as default but we can compute inertia for 2-8)
    inertias = []
    for k in range(2, 9):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)
    elbow_df = pd.DataFrame({'K': range(2, 9), 'Inertia': inertias})
    log.info("Elbow results:\n" + elbow_df.to_string(index=False))

    # Step 4: KMeans with chosen K
    kmeans = KMeans(n_clusters=K, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    # Silhouette score
    sil_score = silhouette_score(X_scaled, clusters)
    log.info(f"Silhouette Score for K={K}: {sil_score:.4f}")

    # Step 5: PCA 2D
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    pca_df = pd.DataFrame(X_pca, columns=['PC1', 'PC2'])

    # Assemble final dataframe
    result_df = df_filtered.copy()
    result_df['cluster'] = clusters
    result_df[['PC1', 'PC2']] = pca_df

    # Also include overall_winrate and total_games for interpretation
    # Already present.

    # Step 6: Save results
    output_path = "data/model3_clusters.parquet"
    result_df.to_parquet(OUTPUT_PATH, index=False)
    log.info(f"Saved results to {OUTPUT_PATH}")

    # Top findings
    log.info("===== CLUSTERING RESULTS =====")
    log.info(f"Number of players: {len(result_df)}")
    log.info(f"Silhouette Score: {sil_score:.4f}")

    # Summary per cluster
    for cluster in sorted(result_df['cluster'].unique()):
        cluster_data = result_df[result_df['cluster'] == cluster]
        avg_winrate = cluster_data['overall_winrate'].mean()
        avg_games = cluster_data['total_games'].mean()
        players = cluster_data['ingame_name'].tolist()
        log.info(f"Cluster {cluster}: {len(cluster_data)} players, avg winrate={avg_winrate:.3f}, avg games={avg_games:.1f}")
        log.info(f"  Players: {', '.join(players)}")

    return result_df


if __name__ == "__main__":
    # Run with default K=3
    run_clustering(K=3)