"""Tests d'intégration de l'API (contrat, validation, métriques)."""
import pytest
from fastapi.testclient import TestClient
from sklearn.pipeline import Pipeline

import impayes.api.main as api
from impayes.config import load_params
from impayes.features.build_features import build_preprocessor, input_columns
from impayes.models.train import make_estimator

VALID = {"tenure_months": 47, "avg_monthly_spend_ngn": 38033.69, "recharge_frequency_per_month": 19,
         "payment_consistency_score": 0.61, "late_payment_count": 1, "operator": "MTN",
         "account_type": "prepaid", "customer_ref": "REF-001"}


@pytest.fixture(scope="module")
def client(sample_df, tmp_path_factory, monkeypatch_module):
    p = load_params()
    pipe = Pipeline([("prep", build_preprocessor()), ("clf", make_estimator("logreg", p))])
    pipe.fit(sample_df[input_columns()], sample_df["default_risk"])
    monkeypatch_module.setenv("PREDICTION_LOG", "0")
    monkeypatch_module.setattr(api, "load_model", lambda: api._state.update(
        model=pipe, meta={"model_name": "test-model", "version": 0}))
    with TestClient(api.app) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_predict_contract(client):
    r = client.post("/predict", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert body["default_risk"] in {"low", "medium", "high"}
    assert abs(sum(body["probabilities"].values()) - 1) < 1e-3
    assert body["customer_ref"] == "REF-001"


@pytest.mark.parametrize("field,value", [
    ("payment_consistency_score", 1.5),      # hors bornes
    ("late_payment_count", -1),              # négatif
    ("operator", "Orange"),                  # catégorie inconnue
    ("tenure_months", "abc"),                # mauvais type
])
def test_invalid_payload_rejected(client, field, value):
    r = client.post("/predict", json=VALID | {field: value})
    assert r.status_code == 422


def test_missing_field_rejected(client):
    payload = {k: v for k, v in VALID.items() if k != "late_payment_count"}
    assert client.post("/predict", json=payload).status_code == 422


def test_batch(client):
    r = client.post("/predict/batch", json={"customers": [VALID, VALID | {"late_payment_count": 9}]})
    assert r.status_code == 200 and len(r.json()["predictions"]) == 2


def test_openapi_and_metrics(client):
    assert "/predict" in client.get("/openapi.json").json()["paths"]
    assert "impayes_predictions_total" in client.get("/metrics").text


def test_admin_reload_requires_token(client):
    assert client.post("/admin/reload").status_code == 403
