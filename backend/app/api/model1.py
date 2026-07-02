from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/shap-importance")
def get_shap_importance(request: Request, top_n: int = 20):
    """
    Trả top features quan trọng nhất theo SHAP.
    Lưu ý: Model 1 có AUC thấp hơn baseline (đã document trong README) —
    endpoint này phục vụ mục đích minh hoạ pipeline + explainability,
    không phải để dùng prediction thực tế.
    """
    cache = request.app.state.cache
    if cache.model1_artifact is None:
        raise HTTPException(status_code=404, detail="Model 1 chưa được train")

    importance = cache.model1_artifact["shap_importance"]
    return importance.head(top_n).to_dict(orient="records")


@router.get("/info")
def get_model1_info(request: Request):
    """Thông tin metadata về model 1 (để hiện disclaimer trên dashboard)."""
    cache = request.app.state.cache
    if cache.model1_artifact is None:
        raise HTTPException(status_code=404, detail="Model 1 chưa được train")

    return {
        "model_type": "LightGBM Classifier",
        "n_features": len(cache.model1_artifact["feature_columns"]),
        "note": (
            "Model đạt AUC ~0.52 trên TimeSeriesSplit, thấp hơn naive baseline "
            "(luôn đoán T1 thắng, 64.45% accuracy). Kết luận: draft + rolling "
            "win rate + player form không đủ explanatory power để predict "
            "outcome — micro-factors (in-game execution, individual plays) "
            "chiếm phần lớn variance. Xem README để biết chi tiết phân tích SHAP."
        ),
    }