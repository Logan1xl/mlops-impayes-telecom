"""Feature engineering + découpage train/val/test (étape DVC « preprocess »).

Le feature engineering est encapsulé dans un transformateur scikit-learn
intégré au pipeline du modèle : la MÊME transformation est appliquée à
l'entraînement et en production par l'API (pas de « training/serving skew »).
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from impayes.config import load_params, path

log = logging.getLogger("impayes.features")

ENGINEERED = ["spend_per_recharge", "late_rate", "log_spend", "is_new_customer"]


class TelecomFeatures(BaseEstimator, TransformerMixin):
    """Ajoute les variables dérivées. Sans état : fit() ne fait rien."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        if not self.enabled:
            return X
        recharge = X["recharge_frequency_per_month"].clip(lower=1)
        tenure = X["tenure_months"].clip(lower=1)
        X["spend_per_recharge"] = X["avg_monthly_spend_ngn"] / recharge
        X["late_rate"] = X["late_payment_count"] / tenure
        X["log_spend"] = np.log1p(X["avg_monthly_spend_ngn"].clip(lower=0))
        X["is_new_customer"] = (X["tenure_months"] < 6).astype(int)
        return X


def feature_columns() -> tuple[list[str], list[str]]:
    f = load_params()["features"]
    numeric = list(f["numeric"]) + (ENGINEERED if f.get("engineered", True) else [])
    return numeric, list(f["categorical"])


def input_columns() -> list[str]:
    f = load_params()["features"]
    return list(f["numeric"]) + list(f["categorical"])


def build_preprocessor() -> Pipeline:
    numeric, categorical = feature_columns()
    ct = ColumnTransformer([
        ("num", StandardScaler(), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
    ], verbose_feature_names_out=False)
    return Pipeline([
        ("features", TelecomFeatures(load_params()["features"].get("engineered", True))),
        ("columns", ct),
    ])


def split_dataset(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    p = load_params()
    target, seed = p["data"]["target"], p["project"]["seed"]
    cols = input_columns() + [target]
    df = df[cols].dropna()
    train_val, test = train_test_split(df, test_size=p["split"]["test_size"],
                                       stratify=df[target], random_state=seed)
    val_rel = p["split"]["val_size"] / (1 - p["split"]["test_size"])
    train, val = train_test_split(train_val, test_size=val_rel,
                                  stratify=train_val[target], random_state=seed)
    return {"train": train, "val": val, "test": test}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = load_params()
    df = pd.read_parquet(path(p["data"]["raw_path"]))
    splits = split_dataset(df)
    out_dir = path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, part in splits.items():
        part.to_parquet(out_dir / f"{name}.parquet", index=False)
        stats[name] = {"rows": len(part),
                       "class_share": part[p["data"]["target"]].value_counts(normalize=True).round(4).to_dict()}
        log.info("%s : %d lignes", name, len(part))

    # Jeu de référence pour la détection de dérive (échantillon du train)
    ref_dir = path("data/reference")
    ref_dir.mkdir(parents=True, exist_ok=True)
    splits["train"].sample(min(50_000, len(splits["train"])), random_state=p["project"]["seed"]) \
        .to_parquet(ref_dir / "reference.parquet", index=False)

    path("reports").mkdir(exist_ok=True)
    path("reports/split_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
