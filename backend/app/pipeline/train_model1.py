"""
Model 1: T1 Win Prediction from Draft + Player Form
Train LightGBM + XGBoost, evaluate, export SHAP values
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import xgboost as xgb
import shap
import pickle
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, roc_auc_score,
    classification_report, confusion_matrix
)

FEATURE_PATH = "data/features_model1.parquet"
MODEL_OUTPUT  = "data/model1_lgbm.pkl"


def load_features(path: str = FEATURE_PATH):
    df = pd.read_parquet(path)
    # Sort theo game id để giữ temporal order
    df = df.sort_values("id_game").reset_index(drop=True)

    X = df.drop(columns=["id_game", "is_t1_win"])
    y = df["is_t1_win"]
    return X, y, df


def train_and_evaluate(X, y):
    """
    Dùng TimeSeriesSplit thay vì random split
    Lý do: data có temporal dependency, random split sẽ leak future info vào past
    """
    tscv = TimeSeriesSplit(n_splits=5)

    lgbm_scores = []
    xgb_scores  = []

    print("=" * 50)
    print("TimeSeriesSplit Cross Validation (5 folds)")
    print("=" * 50)

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # LightGBM
        lgbm_model = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            min_child_samples=10,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1
        )
        lgbm_model.fit(X_train, y_train)
        lgbm_pred = lgbm_model.predict_proba(X_val)[:, 1]
        lgbm_auc  = roc_auc_score(y_val, lgbm_pred)
        lgbm_acc  = accuracy_score(y_val, lgbm_pred >= 0.5)
        lgbm_scores.append((lgbm_auc, lgbm_acc))

        # XGBoost
        xgb_model = xgb.XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="logloss",
            verbosity=0
        )
        xgb_model.fit(X_train, y_train)
        xgb_pred = xgb_model.predict_proba(X_val)[:, 1]
        xgb_auc  = roc_auc_score(y_val, xgb_pred)
        xgb_acc  = accuracy_score(y_val, xgb_pred >= 0.5)
        xgb_scores.append((xgb_auc, xgb_acc))

        print(f"Fold {fold} | LGBM AUC={lgbm_auc:.4f} ACC={lgbm_acc:.4f} | "
              f"XGB AUC={xgb_auc:.4f} ACC={xgb_acc:.4f}")

    lgbm_mean_auc = np.mean([s[0] for s in lgbm_scores])
    lgbm_mean_acc = np.mean([s[1] for s in lgbm_scores])
    xgb_mean_auc  = np.mean([s[0] for s in xgb_scores])
    xgb_mean_acc  = np.mean([s[1] for s in xgb_scores])

    print("=" * 50)
    print(f"LGBM avg | AUC={lgbm_mean_auc:.4f} ACC={lgbm_mean_acc:.4f}")
    print(f"XGB  avg | AUC={xgb_mean_auc:.4f}  ACC={xgb_mean_acc:.4f}")
    print("=" * 50)

    return lgbm_mean_auc, xgb_mean_auc


def train_final_model(X, y):
    """Train trên toàn bộ data sau khi đã evaluate"""
    print("\nTraining final model on full data...")

    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=10,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1
    )
    model.fit(X, y)
    return model


def compute_shap(model, X):
    """SHAP values để explain model — quan trọng cho portfolio"""
    print("\nComputing SHAP values...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # Top 20 features quan trọng nhất
    if isinstance(shap_values, list):
        sv = shap_values[1]  # class 1 (T1 win)
    else:
        sv = shap_values

    importance = pd.DataFrame({
        "feature": X.columns,
        "mean_shap": np.abs(sv).mean(axis=0)
    }).sort_values("mean_shap", ascending=False)

    print("\nTop 20 most important features:")
    print(importance.head(20).to_string(index=False))
    return importance


if __name__ == "__main__":
    print("Loading features...")
    X, y, df = load_features()
    print(f"Dataset: {X.shape[0]} games, {X.shape[1]} features")
    print(f"T1 win rate: {y.mean():.2%}\n")

    # Evaluate
    lgbm_auc, xgb_auc = train_and_evaluate(X, y)

    # Train final
    final_model = train_final_model(X, y)

    # SHAP
    shap_importance = compute_shap(final_model, X)

    # Save model + feature columns (cần khi serve prediction)
    artifact = {
        "model": final_model,
        "feature_columns": list(X.columns),
        "shap_importance": shap_importance
    }
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(artifact, f)

    print(f"\nModel saved to {MODEL_OUTPUT}")