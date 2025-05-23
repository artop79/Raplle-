"""
ML prediction API helper: loads model and predicts candidate success.
"""
import joblib
import numpy as np
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

def predict_success(features: dict):
    """
    features: dict with at least 'score' and 'hr_rating' (others ignored for MVP)
    Returns: probability of success (float 0..1)
    """
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError("Model not trained yet")
    model = joblib.load(MODEL_PATH)
    x = np.array([[features.get("score", 0), features.get("hr_rating", 0)]])
    prob = float(model.predict_proba(x)[0, 1])
    return prob

def explain_success(features: dict, candidate_id=None, true_label=None):
    """
    Возвращает probability, feature_importances, SHAP значения и путь к графику для текущего предсказания.
    Если передан true_label, логирует FP/FN через MLExplainMonitor.
    """
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError("Model not trained yet")
    model = joblib.load(MODEL_PATH)
    feature_names = ["score", "hr_rating"]
    x = np.array([[features.get("score", 0), features.get("hr_rating", 0)]])
    prob = float(model.predict_proba(x)[0, 1])
    importances = getattr(model, 'feature_importances_', [0.5, 0.5])
    # SHAP/LIME
    from app.services.ml_explain_monitor import MLExplainMonitor
    explainer = MLExplainMonitor(model, feature_names)
    shap_values = explainer.explain_shap(x)
    shap_plot_path = explainer.save_shap_plot(x, candidate_id or 'test')
    # Логирование FP/FN
    if true_label is not None and candidate_id is not None:
        pred_label = int(prob >= 0.5)
        if pred_label != true_label:
            explainer.log_fp_fn(candidate_id, dict(zip(feature_names, x[0].tolist())), true_label, pred_label, prob)
    return {
        "probability": prob,
        "feature_importances": dict(zip(feature_names, importances)),
        "features": dict(zip(feature_names, x[0].tolist())),
        "shap_values": shap_values.tolist() if hasattr(shap_values, 'tolist') else shap_values,
        "shap_plot": shap_plot_path
    }

if __name__ == "__main__":
    # For manual testing
    print(predict_success({"score": 80, "hr_rating": 4}))
    print(explain_success({"score": 80, "hr_rating": 4}))
