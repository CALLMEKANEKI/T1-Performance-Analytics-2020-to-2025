# backend/app/pipeline/features.py
import os
import pandas as pd
from sqlalchemy import create_engine, text  # Import thêm 'text' từ sqlalchemy
from dotenv import load_dotenv

load_dotenv()

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    DB_URL = _db_url
else:
    DB_URL = "postgresql://t1_user:t1_password@localhost:5433/t1_analytics"

def load_raw_data(db_url: str = DB_URL) -> pd.DataFrame:
    engine = create_engine(db_url)
    
    # Giữ nguyên câu query dưới dạng text() của SQLAlchemy
    query = text("""
        SELECT
            g.id_game,
            g.date_played,
            g.patch,
            gt.team_id,
            gt.side,
            gt.result,
            gp.player_id,
            gp.champion_id,
            gp.pick_order,
            p.ingame_name,
            p.position,
            c.name as champion_name,
            t.name as team_name
        FROM games g
        JOIN game_teams gt ON g.id_game = gt.game_id
        JOIN game_players gp ON gt.id_game_team = gp.game_team_id
        JOIN players p ON gp.player_id = p.id_player
        JOIN champions c ON gp.champion_id = c.id_champion
        JOIN teams t ON gt.team_id = t.id_team
        ORDER BY g.date_played, g.id_game
    """)
    
    # Dùng SQLAlchemy để thực thi câu lệnh trước, rồi nạp kết quả trực tiếp vào Pandas
    with engine.connect() as conn:
        result = conn.execute(query)
        # Chuyển đổi các hàng dữ liệu (mappings) thành danh sách dict và tạo DataFrame
        df = pd.DataFrame(result.mappings().all())
        
    df["is_win"] = (df["result"] == "WIN").astype(int)
    df["date_played"] = pd.to_datetime(df["date_played"])
    return df

def compute_champion_rolling_winrate(df: pd.DataFrame, window_days: int = 84) -> pd.DataFrame:
    """
    Với mỗi game, tính win rate của champion đó trong 84 ngày TRƯỚC game (không include game hiện tại).
    Dùng Bayesian smoothing để tránh noise khi ít data.
    """
    df = df.sort_values("date_played").copy()
    results = []

    for champ_id, group in df.groupby("champion_id"):
        group = group.copy()
        rolling_wr = []

        for idx, row in group.iterrows():
            cutoff = row["date_played"]
            past = group[group["date_played"] < cutoff]
            past = past[past["date_played"] >= cutoff - pd.Timedelta(days=window_days)]

            picks = len(past)
            wins = past["is_win"].sum()

            # Bayesian smoothing: kéo về 0.5 khi ít data
            alpha = 3
            smoothed = (wins + alpha) / (picks + 2 * alpha)
            rolling_wr.append({
                "id_game": row["id_game"],
                "champion_id": champ_id,
                "champ_rolling_wr": round(smoothed, 4),
                "champ_rolling_picks": picks
            })

        results.extend(rolling_wr)

    return pd.DataFrame(results)


def compute_player_rolling_winrate(df: pd.DataFrame, window_days: int = 84) -> pd.DataFrame:
    """
    Với mỗi game, tính:
    - player_rolling_wr: win rate gần đây của player (mọi champion)
    - player_champ_wr: win rate của player trên champion cụ thể
    - player_champ_games: số lần đã chơi champion này
    """
    df = df.sort_values("date_played").copy()
    results = []

    for player_id, group in df.groupby("player_id"):
        group = group.copy()

        for idx, row in group.iterrows():
            cutoff = row["date_played"]
            past = group[group["date_played"] < cutoff]
            past_window = past[past["date_played"] >= cutoff - pd.Timedelta(days=window_days)]

            # Overall player form
            p_picks = len(past_window)
            p_wins = past_window["is_win"].sum()
            alpha = 3
            player_wr = (p_wins + alpha) / (p_picks + 2 * alpha)

            # Player on this specific champion
            past_champ = past_window[past_window["champion_id"] == row["champion_id"]]
            pc_picks = len(past_champ)
            pc_wins = past_champ["is_win"].sum()
            player_champ_wr = (pc_wins + alpha) / (pc_picks + 2 * alpha)

            results.append({
                "id_game": row["id_game"],
                "player_id": player_id,
                "champion_id": row["champion_id"],
                "player_rolling_wr": round(float(player_wr), 4),
                "player_champ_wr": round(float(player_champ_wr), 4),
                "player_champ_games": pc_picks
            })

    return pd.DataFrame(results)

def build_model1_features(db_url: str = DB_URL) -> pd.DataFrame:
    """
    Output: 1 row = 1 game
    Features: draft (one-hot) + side + patch + champion rolling wr + player form
    Target: is_t1_win (1/0)
    """
    df = load_raw_data(db_url)
    champ_features = compute_champion_rolling_winrate(df)
    player_features = compute_player_rolling_winrate(df)

    # Merge rolling features vào df gốc
    df = df.merge(champ_features, on=["id_game", "champion_id"], how="left")
    df = df.merge(player_features, on=["id_game", "player_id", "champion_id"], how="left")

    # Chỉ lấy T1 side để xác định target
    t1_games = df[df["team_name"] == "T1"][["id_game", "is_win"]].drop_duplicates()
    t1_games = t1_games.rename(columns={"is_win": "is_t1_win"})

    # Pivot: mỗi game có 10 picks (T1: pick 1-5, Opp: pick 1-5)
    # Aggregate features theo game + team side
    def agg_team_features(group, prefix):
        """Tính avg rolling wr của team trong game đó"""
        return pd.Series({
            f"{prefix}_avg_champ_wr": group["champ_rolling_wr"].mean(),
            f"{prefix}_avg_champ_picks": group["champ_rolling_picks"].mean(),
            f"{prefix}_avg_player_wr": group["player_rolling_wr"].mean(),
            f"{prefix}_avg_player_champ_wr": group["player_champ_wr"].mean(),
            f"{prefix}_total_champ_experience": group["player_champ_games"].sum(),
        })

    t1_agg = df[df["team_name"] == "T1"].groupby("id_game").apply(
        lambda g: agg_team_features(g, "t1"), include_groups=False
    ).reset_index()

    opp_agg = df[df["team_name"] != "T1"].groupby("id_game").apply(
        lambda g: agg_team_features(g, "opp"), include_groups=False
    ).reset_index()

    # Side feature (Blue = 1, Red = 0)
    side_df = df[df["team_name"] == "T1"][["id_game", "side"]].drop_duplicates()
    side_df["t1_is_blue"] = (side_df["side"] == "Blue").astype(int)

    # Patch feature
    patch_df = df[["id_game", "patch"]].drop_duplicates()

    # Champion one-hot (T1 picks only)
    t1_picks = df[df["team_name"] == "T1"][["id_game", "champion_id"]].copy()
    t1_picks["val"] = 1
    t1_champ_onehot = t1_picks.pivot_table(
        index="id_game", columns="champion_id", values="val", fill_value=0
    )
    t1_champ_onehot.columns = [f"t1_pick_{c}" for c in t1_champ_onehot.columns]
    t1_champ_onehot = t1_champ_onehot.reset_index()

    # Opponent picks one-hot
    opp_picks = df[df["team_name"] != "T1"][["id_game", "champion_id"]].copy()
    opp_picks["val"] = 1
    opp_champ_onehot = opp_picks.pivot_table(
        index="id_game", columns="champion_id", values="val", fill_value=0
    )
    opp_champ_onehot.columns = [f"opp_pick_{c}" for c in opp_champ_onehot.columns]
    opp_champ_onehot = opp_champ_onehot.reset_index()

    # Merge tất cả lại
    feature_df = t1_games.copy()
    for other in [t1_agg, opp_agg, side_df[["id_game", "t1_is_blue"]], 
                  patch_df, t1_champ_onehot, opp_champ_onehot]:
        feature_df = feature_df.merge(other, on="id_game", how="left")

    # Encode patch thành number (10.1 → 101, 14.5 → 145)
    feature_df["patch_num"] = (
        feature_df["patch"]
        .str.replace(".", "", regex=False)
        .str.extract(r"(\d+)")
        .astype(float)
    )
    feature_df = feature_df.drop(columns=["patch"])

    print(f"\nFeature table shape: {feature_df.shape}")
    print(f"Target distribution: {feature_df['is_t1_win'].value_counts().to_dict()}")
    return feature_df


if __name__ == "__main__":
    print("Loading raw data...")
    df = load_raw_data()
    print(f"Loaded {len(df)} rows")

    print("\nBuilding Model 1 feature table...")
    feature_df = build_model1_features()
    print(feature_df.head(3))
    
    # Save để dùng lại, không phải tính lại mỗi lần
    feature_df.to_parquet("data/features_model1.parquet", index=False)
    print("\nSaved to data/features_model1.parquet")