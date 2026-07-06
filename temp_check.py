from app.pipeline.features import load_raw_data
from app.pipeline.model3_player_clustering import build_player_feature_matrix

df = load_raw_data()
for min_games in [5, 10, 20, 30, 50]:
    feature_df, feature_cols = build_player_feature_matrix(df, min_games=min_games)
    print(min_games, len(feature_df))
    print(feature_df[["player_name", "total_games"]].sort_values("total_games").to_string(index=False))
    print("---")
