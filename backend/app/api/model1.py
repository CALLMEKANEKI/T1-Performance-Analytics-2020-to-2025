from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/shap-importance")
def get_shap_importance(request: Request, top_n: int = 20):
    cache = request.app.state.cache
    if cache.model1_artifact is None:
        raise HTTPException(
            status_code=404, 
            detail="Model 1 artifact chưa được load trong cache. Hãy kiểm tra lại file model."
        )

    importance = cache.model1_artifact["shap_importance"]
    return importance.head(top_n).to_dict(orient="records")


@router.get("/info")
def get_model1_info(request: Request):
    cache = request.app.state.cache
    if cache.model1_artifact is None:
        raise HTTPException(
            status_code=404, 
            detail="Model 1 artifact chưa được load trong cache. Hãy kiểm tra lại file model."
        )

    # Lấy metrics từ artifact nếu có lưu, hoặc trả về cấu trúc chuẩn cho Frontend
    artifact = cache.model1_artifact

    return {
        "model_type": "LightGBM Classifier",
        "n_features": len(artifact.get("feature_columns", [])),
        "training_games": artifact.get("training_games", "903 games"),
        "training_period": artifact.get("training_period", "2020–2025"),
        "metrics": artifact.get("metrics", {
            "auc": 0.53,
            "accuracy": 55.7,
            "baseline_accuracy": 64.45,
            "accuracy_diff": -8.75
        }),
        "folds": artifact.get("folds", [
            {"fold": 1, "auc": 0.35, "period": "2020–2021", "note": "Cold start"},
            {"fold": 2, "auc": 0.57, "period": "2021–2022", "note": "Roster ổn định"},
            {"fold": 3, "auc": 0.54, "period": "2022–2023", "note": "—"},
            {"fold": 4, "auc": 0.59, "period": "2023–2024", "note": "Tốt nhất"},
            {"fold": 5, "auc": 0.60, "period": "2024–2025", "note": "Tốt nhất"}
        ]),
        "note": (
            "Model đạt AUC ~0.53 trên TimeSeriesSplit, thấp hơn naive baseline "
            "(luôn đoán T1 thắng, 64.45% accuracy). Kết luận: draft + rolling "
            "win rate + player form không đủ explanatory power để predict "
            "outcome — micro-factors (in-game execution, individual plays) "
            "chiếm phần lớn variance."
        ),
    }
