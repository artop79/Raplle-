from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import analysis, auth, heygen
from app.routers import telegram_bot, hr_agent
from app.api.error_handlers import add_global_exception_handlers
from app.database.session import get_db
from app.database.models import Base
from app.database.session import engine
from app.config import settings
from app.services.feedback_schemas import FeedbackCreate, FeedbackOut
from app.database import models
import os
import shutil
import tempfile
import datetime
from fastapi.responses import JSONResponse, StreamingResponse
import io
import csv
import subprocess
import json as pyjson
from fastapi import Request

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Подключаем глобальные обработчики ошибок
add_global_exception_handlers(app)

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшн режиме нужно указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ML Monitoring & Explainability endpoints ---
import os
from fastapi.responses import FileResponse
from app.services.ml_explain_monitor import MLExplainMonitor

@app.get("/api/ml/shap_plot/{filename}")
def get_shap_plot(filename: str):
    # Безопасность: только PNG из текущей папки
    if not filename.startswith('shap_') or not filename.endswith('.png'):
        return JSONResponse(status_code=400, content={"error": "Invalid filename"})
    if not os.path.exists(filename):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return FileResponse(filename, media_type="image/png")

from fastapi import Query
from fastapi.responses import StreamingResponse
import io
import csv

@app.get("/api/ml/fpfn_log")
def get_fpfn_log(
    date_from: str = Query(None),
    date_to: str = Query(None),
    candidate_id: str = Query(None),
    error_type: str = Query("all", regex="^(fp|fn|all)$")
):
    log = MLExplainMonitor.get_fp_fn_log()
    # Фильтрация по дате
    if date_from:
        log = [e for e in log if e['timestamp'] >= date_from]
    if date_to:
        log = [e for e in log if e['timestamp'] <= date_to]
    if candidate_id:
        log = [e for e in log if str(e['candidate_id']) == str(candidate_id)]
    if error_type != "all":
        log = [e for e in log if (error_type == "fp" and e['true_label']==0 and e['pred_label']==1) or (error_type == "fn" and e['true_label']==1 and e['pred_label']==0)]
    return {"log": log}

@app.get("/api/ml/fpfn_log.csv")
def download_fpfn_log_csv(
    date_from: str = Query(None),
    date_to: str = Query(None),
    candidate_id: str = Query(None),
    error_type: str = Query("all", regex="^(fp|fn|all)$")
):
    log = MLExplainMonitor.get_fp_fn_log()
    if date_from:
        log = [e for e in log if e['timestamp'] >= date_from]
    if date_to:
        log = [e for e in log if e['timestamp'] <= date_to]
    if candidate_id:
        log = [e for e in log if str(e['candidate_id']) == str(candidate_id)]
    if error_type != "all":
        log = [e for e in log if (error_type == "fp" and e['true_label']==0 and e['pred_label']==1) or (error_type == "fn" and e['true_label']==1 and e['pred_label']==0)]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(log[0].keys()) if log else [])
    writer.writeheader()
    for row in log:
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=fpfn_log.csv"})

@app.get("/api/ml/drift_log")
def get_drift_log(
    date_from: str = Query(None),
    date_to: str = Query(None)
):
    log = MLExplainMonitor.get_drift_log()
    if date_from:
        log = [e for e in log if e['timestamp'] >= date_from]
    if date_to:
        log = [e for e in log if e['timestamp'] <= date_to]
    return {"log": log}

@app.get("/api/ml/drift_log.csv")
def download_drift_log_csv(
    date_from: str = Query(None),
    date_to: str = Query(None)
):
    log = MLExplainMonitor.get_drift_log()
    if date_from:
        log = [e for e in log if e['timestamp'] >= date_from]
    if date_to:
        log = [e for e in log if e['timestamp'] <= date_to]
    output = io.StringIO()
    if log:
        keys = ['timestamp'] + list(log[0]['drift_metrics'].keys())
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader()
        for row in log:
            flat = {'timestamp': row['timestamp']}
            flat.update(row['drift_metrics'])
            writer.writerow(flat)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=drift_log.csv"})

@app.get("/api/ml/drift_alert")
def get_drift_alert():
    log = MLExplainMonitor.get_drift_log()
    if not log:
        return {"alert": False, "reason": "no drift data"}
    last = log[-1]["drift_metrics"]
    alert = False
    reasons = []
    if last.get("score_ks_p", 1) < 0.05:
        alert = True
        reasons.append("score drift detected (KS p < 0.05)")
    if last.get("hr_ks_p", 1) < 0.05:
        alert = True
        reasons.append("hr_rating drift detected (KS p < 0.05)")
    return {"alert": alert, "reasons": reasons, "drift": last}

# Добавляем маршруты
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_STR}/analysis", tags=["analysis"])
app.include_router(heygen.router, prefix=f"{settings.API_V1_STR}/heygen", tags=["heygen"])
# Важно не дублировать префикс - он уже указан в маршрутизаторе
app.include_router(telegram_bot.router, tags=["automation"])
app.include_router(hr_agent.router, tags=["ai-hr-agent"])

@app.get("/")
def root():
    return {
        "message": "Добро пожаловать в API системы анализа резюме",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Проверка работоспособности API и соединения с базой данных"""
    try:
        # Проверяем соединение с базой данных
        db.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "db_status": db_status
    }

@app.get("/api/feedback/dataset")
def get_feedback_dataset(db: Session = Depends(get_db)):
    analyses = db.query(models.AnalysisResult).all()
    result = []
    for a in analyses:
        feedbacks = db.query(models.AnalysisFeedback).filter(models.AnalysisFeedback.analysis_id == a.id).all()
        feedback_list = [
            {
                "hr_rating": f.hr_rating,
                "is_successful": f.is_successful,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in feedbacks
        ]
        # Исключаем персональные данные, берем только score и results (skills, experience, и т.д.)
        result.append({
            "analysis_id": a.id,
            "score": a.score,
            "results": a.results,  # Здесь могут быть skills, experience, education, risks и др.
            "feedback": feedback_list
        })
    return JSONResponse(content=result)

@app.get("/api/feedback/dataset/csv")
def get_feedback_dataset_csv(
    date_from: str = None,
    date_to: str = None,
    is_successful: bool = None,
    db: Session = Depends(get_db)
):
    analyses = db.query(models.AnalysisResult).all()
    rows = []
    for a in analyses:
        feedbacks = db.query(models.AnalysisFeedback).filter(models.AnalysisFeedback.analysis_id == a.id)
        if date_from:
            feedbacks = feedbacks.filter(models.AnalysisFeedback.created_at >= date_from)
        if date_to:
            feedbacks = feedbacks.filter(models.AnalysisFeedback.created_at <= date_to)
        if is_successful is not None:
            feedbacks = feedbacks.filter(models.AnalysisFeedback.is_successful == is_successful)
        for f in feedbacks:
            row = {
                'analysis_id': a.id,
                'score': a.score,
                'hr_rating': f.hr_rating,
                'is_successful': f.is_successful,
                'created_at': f.created_at.isoformat() if f.created_at else '',
            }
            # Вытаскиваем основные признаки из results (skills, experience, и др.)
            results = a.results or {}
            row['skills'] = str(results.get('skills', ''))
            row['experience'] = str(results.get('experience', ''))
            row['education'] = str(results.get('education', ''))
            row['risks'] = str(results.get('risks', ''))
            # Можно добавить другие поля по необходимости
            rows.append(row)
    # Формируем CSV
    output = io.StringIO()
    fieldnames = ['analysis_id','score','hr_rating','is_successful','created_at','skills','experience','education','risks']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type='text/csv', headers={"Content-Disposition": "attachment; filename=feedback_dataset.csv"})

@app.post("/api/ml/train")
def train_ml_model():
    """
    Запускает обучение модели (train_model.py) и возвращает метрики.
    """
    try:
        result = subprocess.run([
            "python3", "app/train_model.py"
        ], capture_output=True, text=True, check=True)
        # Парсим метрики из вывода
        lines = result.stdout.splitlines()
        metrics_line = next((l for l in lines if l.startswith("Metrics:")), None)
        metrics = metrics_line.replace("Metrics:", "").strip() if metrics_line else None
        try:
            metrics = pyjson.loads(metrics.replace("'", '"')) if metrics else {}
        except Exception:
            metrics = {"raw": metrics}
        return {"status": "ok", "metrics": metrics}
    except subprocess.CalledProcessError as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": e.stderr})

from fastapi import Query

@app.post("/api/ml/score")
def ml_predict_score(request: Request, details: bool = Query(False)):
    """
    Принимает JSON с признаками (score, hr_rating), возвращает вероятность успешности кандидата.
    Если details=true, возвращает подробности ML-решения.
    """
    import sys
    sys.path.append("app")
    from predict_model import predict_success, explain_success
    try:
        data = pyjson.loads(request._body.decode()) if hasattr(request, '_body') and request._body else {}
    except Exception:
        data = {}
    # Для FastAPI >= 0.95 лучше использовать await request.json(), но для синхронности:
    if not data:
        try:
            data = request.json()
        except Exception:
            data = {}
    try:
        if details:
            result = explain_success(data)
            return result
        else:
            prob = predict_success(data)
            return {"probability": prob}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/ml/errors")
def ml_error_analysis():
    """
    Аналитика ошибок ML: TP, TN, FP, FN, метрики, списки ошибок.
    """
    import pandas as pd
    import numpy as np
    import sys
    sys.path.append("app")
    from predict_model import predict_success
    import requests
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

    # 1. Получить датасет
    dataset_url = "http://localhost:8000/api/feedback/dataset/csv"
    r = requests.get(dataset_url)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    df = df.dropna(subset=["is_successful"]).copy()
    df["is_successful"] = df["is_successful"].astype(int)
    # 2. Предсказания
    preds = []
    for _, row in df.iterrows():
        features = {"score": row["score"], "hr_rating": row["hr_rating"]}
        try:
            prob = predict_success(features)
        except Exception:
            prob = 0.5
        preds.append(prob)
    df["ml_prob"] = preds
    df["ml_pred"] = (df["ml_prob"] >= 0.5).astype(int)
    # 3. Метрики
    y_true = df["is_successful"].values
    y_pred = df["ml_pred"].values
    y_prob = df["ml_prob"].values
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred)),
        "recall": float(recall_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(set(y_true)) > 1 else None
    }
    # 4. Ошибки
    fp = df[(df["ml_pred"] == 1) & (df["is_successful"] == 0)]
    fn = df[(df["ml_pred"] == 0) & (df["is_successful"] == 1)]
    tp = df[(df["ml_pred"] == 1) & (df["is_successful"] == 1)]
    tn = df[(df["ml_pred"] == 0) & (df["is_successful"] == 0)]
    def to_list(d):
        return d[["score", "hr_rating", "ml_prob", "is_successful"]].to_dict(orient="records")
    return {
        "metrics": metrics,
        "total": len(df),
        "TP": len(tp),
        "TN": len(tn),
        "FP": len(fp),
        "FN": len(fn),
        "false_positives": to_list(fp),
        "false_negatives": to_list(fn)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
