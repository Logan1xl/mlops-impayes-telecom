"""API de serving du modèle de prédiction des impayés.

Lancement local :  uvicorn impayes.api.main:app --reload --port 8000
Documentation   :  http://localhost:8000/docs  (Swagger / OpenAPI)

Source du modèle (variable MODEL_SOURCE) :
  - "local"    (défaut) : models/model.joblib embarqué dans l'image Docker ;
  - "registry"          : models:/<nom>@production depuis le serveur MLflow.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from impayes.api.schemas import BatchRequest, BatchResponse, Feedback, ModelInfo, PredictionRequest, PredictionResponse
from impayes.config import load_params, path, tracking_uri

log = logging.getLogger("impayes.api")
FEATURES = ["tenure_months", "avg_monthly_spend_ngn", "recharge_frequency_per_month",
            "payment_consistency_score", "late_payment_count", "operator", "account_type"]

# ---- Métriques Prometheus (scrapées par Prometheus, affichées dans Grafana) ----
REQUESTS = Counter("impayes_requests_total", "Requêtes reçues", ["endpoint", "status"])
LATENCY = Histogram("impayes_inference_latency_seconds", "Latence d'inférence",
                    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2))
PREDICTIONS = Counter("impayes_predictions_total", "Prédictions par classe", ["default_risk"])
FEATURE_MEAN = Gauge("impayes_feature_mean", "Moyenne glissante des variables d'entrée", ["feature"])
MODEL_VERSION = Gauge("impayes_model_version", "Version du modèle servi")

_state: dict = {}
_lock = threading.Lock()
_window: list[dict] = []


def load_model() -> None:
    p = load_params()
    source = os.getenv("MODEL_SOURCE", "local")
    meta_path = path("models/model_metadata.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if source == "registry":
        import mlflow
        mlflow.set_tracking_uri(tracking_uri())
        name = p["registry"]["model_name"]
        alias = os.getenv("MODEL_ALIAS", "production")
        mv = mlflow.MlflowClient().get_model_version_by_alias(name, alias)
        model = mlflow.sklearn.load_model(f"models:/{name}@{alias}")
        meta |= {"version": int(mv.version), "run_id": mv.run_id, "model_type": mv.tags.get("model_type")}
    else:
        model = joblib.load(path(os.getenv("MODEL_PATH", "models/model.joblib")))
    _state.update(model=model, meta=meta | {"model_name": p["registry"]["model_name"]})
    MODEL_VERSION.set(float(meta.get("version", 0)))
    log.info("Modèle chargé (%s) : v%s", source, meta.get("version"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    load_model()
    yield


app = FastAPI(
    title="API Prédiction des impayés télécom",
    version="1.0.0",
    description="Prédit le niveau de risque d'impayé (low / medium / high) d'un abonné "
                "à partir de son comportement d'usage et de paiement.",
    lifespan=lifespan,
)


def _log_prediction(record: dict) -> None:
    """Journalise entrée + sortie (sans donnée personnelle) pour le monitoring de dérive."""
    if os.getenv("PREDICTION_LOG", "1") != "1":
        return
    f = path("data/production/predictions.jsonl")
    f.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        _window.append(record)
        del _window[:-500]
        for feat in FEATURES[:5]:
            FEATURE_MEAN.labels(feat).set(sum(r[feat] for r in _window) / len(_window))


def _predict(rows: list[PredictionRequest]) -> list[PredictionResponse]:
    model, meta = _state["model"], _state["meta"]
    X = pd.DataFrame([r.model_dump(include=set(FEATURES)) for r in rows])[FEATURES]
    t0 = time.perf_counter()
    proba = model.predict_proba(X)
    elapsed = time.perf_counter() - t0
    LATENCY.observe(elapsed)
    classes = list(model.classes_)
    out = []
    for r, pr in zip(rows, proba, strict=True):
        label = classes[int(pr.argmax())]
        PREDICTIONS.labels(label).inc()
        rid = str(uuid.uuid4())
        resp = PredictionResponse(request_id=rid, customer_ref=r.customer_ref, default_risk=label,
                                  probabilities={c: round(float(v), 4) for c, v in zip(classes, pr, strict=True)},
                                  model_name=meta["model_name"], model_version=meta.get("version", "unknown"),
                                  latency_ms=round(elapsed * 1000 / len(rows), 3))
        _log_prediction({"request_id": rid, "ts": datetime.now(timezone.utc).isoformat(),
                         **r.model_dump(include=set(FEATURES)), "prediction": label,
                         "model_version": resp.model_version, "latency_ms": resp.latency_ms})
        out.append(resp)
    return out


@app.get("/health", tags=["exploitation"])
def health() -> dict:
    """Sonde de vivacité/disponibilité (utilisée par Docker et Kubernetes)."""
    return {"status": "ok" if "model" in _state else "loading",
            "model_version": _state.get("meta", {}).get("version")}


@app.get("/model-info", response_model=ModelInfo, tags=["exploitation"])
def model_info() -> ModelInfo:
    m = _state["meta"]
    return ModelInfo(model_name=m["model_name"], model_version=m.get("version", "unknown"),
                     model_type=m.get("model_type"), run_id=m.get("run_id"), trained_at=m.get("trained_at"),
                     data_version=m.get("data_version"), classes=list(_state["model"].classes_),
                     features=FEATURES)


@app.post("/predict", response_model=PredictionResponse, tags=["prédiction"])
def predict(req: PredictionRequest) -> PredictionResponse:
    """Prédit le risque d'impayé d'un client."""
    try:
        res = _predict([req])[0]
        REQUESTS.labels("predict", "200").inc()
        return res
    except Exception as exc:  # pragma: no cover
        REQUESTS.labels("predict", "500").inc()
        log.exception("Erreur d'inférence")
        raise HTTPException(500, "Erreur d'inférence") from exc


@app.post("/predict/batch", response_model=BatchResponse, tags=["prédiction"])
def predict_batch(req: BatchRequest) -> BatchResponse:
    """Scoring par lot (jusqu'à 1000 clients), ex. campagne mensuelle."""
    res = _predict(req.customers)
    REQUESTS.labels("predict_batch", "200").inc()
    return BatchResponse(predictions=res)


@app.post("/feedback", status_code=202, tags=["monitoring"])
def feedback(fb: Feedback) -> dict:
    """Reçoit l'issue réelle (impayé constaté) pour mesurer le concept drift."""
    f = path("data/production/feedback.jsonl")
    f.parent.mkdir(parents=True, exist_ok=True)
    with _lock, open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(fb.model_dump() | {"ts": datetime.now(timezone.utc).isoformat()}) + "\n")
    REQUESTS.labels("feedback", "202").inc()
    return {"status": "accepted"}


@app.post("/admin/reload", tags=["exploitation"])
def reload_model(request: Request) -> dict:
    """Recharge le modèle (après promotion dans le registre). Protégé par jeton."""
    token = os.getenv("ADMIN_TOKEN")
    if not token or request.headers.get("x-admin-token") != token:
        raise HTTPException(403, "Accès refusé")
    load_model()
    return {"status": "reloaded", "model_version": _state["meta"].get("version")}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
