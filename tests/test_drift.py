"""Tests du module de détection de dérive."""
import pandas as pd

from impayes.data.synthetic import generate
from impayes.features.build_features import input_columns
from impayes.monitoring.drift import analyse, psi_categorical, psi_numeric


def test_psi_zero_on_identical_distributions(sample_df):
    s = sample_df["avg_monthly_spend_ngn"]
    assert psi_numeric(s, s) < 1e-6


def test_psi_detects_shift(sample_df):
    s = sample_df["avg_monthly_spend_ngn"]
    assert psi_numeric(s, s * 1.6) > 0.25


def test_psi_categorical_new_category():
    ref = pd.Series(["MTN"] * 50 + ["Glo"] * 50)
    cur = pd.Series(["MTN"] * 30 + ["Glo"] * 30 + ["Nouveau"] * 40)
    assert psi_categorical(ref, cur) > 0.25


def test_no_drift_no_action(sample_df):
    cols = input_columns()
    other = generate(20_000, seed=99)
    rep = analyse(sample_df[cols], other[cols])
    assert rep.data_drift == "OK" and rep.decision == "none"


def test_data_drift_alone_does_not_retrain(sample_df):
    """R10.3 : une dérive des données sans perte de performance => analyse, pas de remplacement."""
    cols = input_columns()
    drifted = generate(20_000, seed=3, spend_shift=1.7)
    rep = analyse(sample_df[cols], drifted[cols])
    assert rep.data_drift == "CRITICAL"
    assert rep.decision == "investigate"


def test_concept_drift_triggers_retraining(sample_df):
    cols = input_columns()
    batch = generate(5_000, seed=4)
    y = batch["default_risk"]
    wrong = y.map({"low": "medium", "medium": "high", "high": "low"})  # prédictions dégradées
    rep = analyse(sample_df[cols], batch[cols], cur_pred=wrong, y_true=y, f1_reference=0.65)
    assert rep.concept_drift == "CRITICAL"
    assert rep.decision == "trigger_retraining"
