import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from app.pipeline.features import load_raw_data
from app.pipeline.model3_player_clustering import build_player_feature_matrix

df = load_raw_data()
feature_df, feature_cols = build_player_feature_matrix(df, min_games=20)
X = feature_df[feature_cols].fillna(0).astype(float).copy()
for col in ['total_games', 'champ_pool_size', 'avg_games_per_champ']:
    X[col] = np.log1p(X[col])
X_scaled = StandardScaler().fit_transform(X)
for n_comp in [2, 3, 4]:
    pca = PCA(n_components=n_comp, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    labels = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(X_pca)
    s = silhouette_score(X_pca, labels)
    print(f'n_comp={n_comp} silhouette={s:.4f}')
