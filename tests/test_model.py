"""Tests comportementaux du modèle (entraîné sur un petit échantillon)."""
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

from impayes.config import load_params
from impayes.features.build_features import build_preprocessor, input_columns, split_dataset
from impayes.models.train import make_estimator


@pytest.fixture(scope="module")
def trained(sample_df):
    s = split_dataset(sample_df)
    cols = input_columns()
    pipe = Pipeline([("prep", build_preprocessor()), ("clf", make_estimator("hist_gbm", load_params()))])
    pipe.fit(s["train"][cols], s["train"]["default_risk"])
    return pipe, s


def test_beats_naive_baseline(trained):
    pipe, s = trained
    cols = input_columns()
    dummy = DummyClassifier(strategy="most_frequent").fit(s["train"][cols], s["train"]["default_risk"])
    y = s["test"]["default_risk"]
    f1_model = f1_score(y, pipe.predict(s["test"][cols]), average="macro")
    f1_dummy = f1_score(y, dummy.predict(s["test"][cols]), average="macro")
    assert f1_model > f1_dummy + 0.2


def test_probabilities_are_valid(trained):
    pipe, s = trained
    proba = pipe.predict_proba(s["test"][input_columns()].head(100))
    assert ((proba >= 0) & (proba <= 1)).all()
    assert abs(proba.sum(axis=1) - 1).max() < 1e-6


def test_more_late_payments_increase_risk(trained):
    """Test d'invariance directionnelle : + de retards => P(high) ne doit pas baisser."""
    pipe, _ = trained
    base = {"tenure_months": 40, "avg_monthly_spend_ngn": 15000.0, "recharge_frequency_per_month": 10,
            "payment_consistency_score": 0.5, "operator": "MTN", "account_type": "prepaid"}
    X = pd.DataFrame([{**base, "late_payment_count": k} for k in (0, 3, 8)])
    p_high = pipe.predict_proba(X)[:, list(pipe.classes_).index("high")]
    assert p_high[0] <= p_high[1] <= p_high[2]


def test_operator_change_has_limited_effect(trained):
    """Équité / robustesse : changer d'opérateur ne doit pas renverser la décision."""
    pipe, s = trained
    X = s["test"][input_columns()].head(500).copy()
    pred = pipe.predict(X)
    X2 = X.assign(operator="Glo")
    assert (pipe.predict(X2) == pred).mean() > 0.9
