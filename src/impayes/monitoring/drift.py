"""Détection de dérive : data drift (PSI, KS, chi²) et concept drift (F1 sur
labels réels), avec une règle de décision explicite pour le réentraînement.

La décision n'entraîne JAMAIS un remplacement automatique du modèle : elle
déclenche au plus le pipeline de Continuous Training, dont le résultat doit
encore franchir la quality gate puis une validation humaine (voir rapport,
question R10.3).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import f1_score

from impayes.config import load_params

EPS = 1e-6


def psi_numeric(ref: pd.Series, cur: pd.Series, bins: int = 10) -> float:
    """Population Stability Index avec des bornes fixées sur les quantiles de référence."""
    edges = np.unique(np.quantile(ref.dropna(), np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:  # variable quasi constante
        edges = np.unique(np.concatenate([[ref.min() - EPS], ref.unique(), [ref.max() + EPS]]))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / max(len(ref), 1)
    c = np.histogram(cur, edges)[0] / max(len(cur), 1)
    r, c = np.clip(r, EPS, None), np.clip(c, EPS, None)
    return float(np.sum((c - r) * np.log(c / r)))


def psi_categorical(ref: pd.Series, cur: pd.Series) -> float:
    cats = sorted(set(ref.unique()) | set(cur.unique()))
    r = ref.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    c = cur.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    r, c = np.clip(r, EPS, None), np.clip(c, EPS, None)
    return float(np.sum((c - r) * np.log(c / r)))


@dataclass
class FeatureDrift:
    feature: str
    kind: str
    psi: float
    test: str
    p_value: float
    status: str


@dataclass
class DriftReport:
    n_reference: int
    n_current: int
    features: list[FeatureDrift] = field(default_factory=list)
    prediction_psi: float | None = None
    f1_reference: float | None = None
    f1_current: float | None = None
    n_labels: int = 0
    latency_p95_ms: float | None = None
    data_drift: str = "OK"
    concept_drift: str = "OK"
    operational: str = "OK"
    decision: str = "none"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["features"] = [asdict(f) for f in self.features]
        return d


def _status(psi: float, p: dict) -> str:
    m = p["monitoring"]
    return "CRITICAL" if psi >= m["psi_critical"] else "WARNING" if psi >= m["psi_warning"] else "OK"


def feature_drift(reference: pd.DataFrame, current: pd.DataFrame) -> list[FeatureDrift]:
    p = load_params()
    out = []
    for col in p["features"]["numeric"]:
        psi = psi_numeric(reference[col], current[col])
        pval = float(stats.ks_2samp(reference[col], current[col]).pvalue)
        out.append(FeatureDrift(col, "numeric", round(psi, 4), "KS", pval, _status(psi, p)))
    for col in p["features"]["categorical"]:
        psi = psi_categorical(reference[col], current[col])
        cats = sorted(set(reference[col]) | set(current[col]))
        table = np.array([reference[col].value_counts().reindex(cats, fill_value=0),
                          current[col].value_counts().reindex(cats, fill_value=0)])
        pval = float(stats.chi2_contingency(table + 1)[1])
        out.append(FeatureDrift(col, "categorical", round(psi, 4), "chi2", pval, _status(psi, p)))
    return out


def analyse(reference: pd.DataFrame, current: pd.DataFrame, *,
            ref_pred: pd.Series | None = None, cur_pred: pd.Series | None = None,
            f1_reference: float | None = None, y_true: pd.Series | None = None,
            latency_ms: np.ndarray | None = None) -> DriftReport:
    """Analyse complète d'un lot de production et règle de décision."""
    p = load_params()
    m = p["monitoring"]
    rep = DriftReport(len(reference), len(current), feature_drift(reference, current))

    n_crit = sum(f.status == "CRITICAL" for f in rep.features)
    n_warn = sum(f.status == "WARNING" for f in rep.features)
    if n_crit:
        rep.data_drift = "CRITICAL"
        rep.reasons.append(f"{n_crit} variable(s) avec PSI >= {m['psi_critical']}")
    elif n_warn:
        rep.data_drift = "WARNING"
        rep.reasons.append(f"{n_warn} variable(s) avec PSI >= {m['psi_warning']}")

    if ref_pred is not None and cur_pred is not None:
        rep.prediction_psi = round(psi_categorical(ref_pred, cur_pred), 4)

    if y_true is not None and cur_pred is not None and f1_reference is not None:
        rep.n_labels = int(len(y_true))
        rep.f1_reference = f1_reference
        if rep.n_labels >= m["min_labels_for_concept_check"]:
            rep.f1_current = float(f1_score(y_true, cur_pred, average="macro"))
            drop = f1_reference - rep.f1_current
            if drop >= m["f1_drop_critical"]:
                rep.concept_drift = "CRITICAL"
                rep.reasons.append(f"F1-macro en baisse de {drop:.3f} (>= {m['f1_drop_critical']})")
            elif drop >= m["f1_drop_warning"]:
                rep.concept_drift = "WARNING"
                rep.reasons.append(f"F1-macro en baisse de {drop:.3f} (>= {m['f1_drop_warning']})")

    if latency_ms is not None and len(latency_ms):
        rep.latency_p95_ms = float(np.percentile(latency_ms, 95))
        if rep.latency_p95_ms > m["latency_p95_ms_critical"]:
            rep.operational = "CRITICAL"
            rep.reasons.append(f"latence p95 {rep.latency_p95_ms:.0f} ms > {m['latency_p95_ms_critical']} ms")

    # Règle de décision (cf. plan de monitoring du rapport)
    if rep.concept_drift == "CRITICAL":
        rep.decision = "trigger_retraining"          # perf réelle dégradée : CT + revue humaine
    elif rep.data_drift == "CRITICAL" and rep.concept_drift == "WARNING":
        rep.decision = "trigger_retraining"
    elif rep.data_drift == "CRITICAL":
        rep.decision = "investigate"                 # dérive sans preuve de perte de perf
    elif "WARNING" in (rep.data_drift, rep.concept_drift):
        rep.decision = "watch"
    if rep.operational == "CRITICAL":
        rep.decision = rep.decision if rep.decision == "trigger_retraining" else "scale_or_optimize"
    return rep
