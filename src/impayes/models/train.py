"""Étape « train » : entraîne et compare les modèles candidats, trace tout
dans MLflow et enregistre le meilleur dans le Model Registry (alias
« candidate »). La promotion vers staging/production est faite par
evaluate.py (quality gate) puis registry.py (validation humaine).
"""
from __future__ import annotations

import json
import logging
import platform
import subprocess
import time

import joblib
import mlflow
import numpy as np
import pandas as pd
import sklearn
from mlflow.models import infer_signature
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline

from impayes.config import load_params, path, tracking_uri
from impayes.features.build_features import build_preprocessor, input_columns

log = logging.getLogger("impayes.train")


def make_estimator(name: str, p: dict):
    t, seed, cw = p["train"], p["project"]["seed"], p["train"]["class_weight"]
    if name == "logreg":
        return LogisticRegression(C=t["logreg"]["C"], max_iter=t["logreg"]["max_iter"],
                                  class_weight=cw, random_state=seed)
    if name == "random_forest":
        rf = t["random_forest"]
        return RandomForestClassifier(n_estimators=rf["n_estimators"], max_depth=rf["max_depth"],
                                      min_samples_leaf=rf["min_samples_leaf"], class_weight=cw,
                                      n_jobs=-1, random_state=seed)
    if name == "hist_gbm":
        hg = t["hist_gbm"]
        return HistGradientBoostingClassifier(max_iter=hg["max_iter"], learning_rate=hg["learning_rate"],
                                              max_leaf_nodes=hg["max_leaf_nodes"],
                                              l2_regularization=hg["l2_regularization"],
                                              class_weight=cw, random_state=seed)
    raise ValueError(f"Modèle inconnu : {name}")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "no-git"


def data_version() -> str:
    """Hash DVC du fichier brut s'il existe (lien modèle <-> données)."""
    dvc_file = path(load_params()["data"]["raw_path"] + ".dvc")
    if dvc_file.exists():
        for line in dvc_file.read_text().splitlines():
            if "md5:" in line:
                return line.split("md5:")[1].strip()
    src = path("data/raw/SOURCE.json")
    return json.loads(src.read_text())["source"] if src.exists() else "unknown"


def score(model, X: pd.DataFrame, y: pd.Series, classes: list[str]) -> dict[str, float]:
    pred = model.predict(X)
    proba = model.predict_proba(X)
    return {
        "f1_macro": f1_score(y, pred, average="macro"),
        "recall_high": recall_score(y, pred, labels=["high"], average="macro"),
        "auc_ovr_macro": roc_auc_score(y, proba, multi_class="ovr", average="macro",
                                       labels=list(model.classes_)),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = load_params()
    seed, target, classes = p["project"]["seed"], p["data"]["target"], p["data"]["classes"]
    np.random.seed(seed)

    train = pd.read_parquet(path("data/processed/train.parquet"))
    val = pd.read_parquet(path("data/processed/val.parquet"))
    cols = input_columns()
    X_tr, y_tr, X_va, y_va = train[cols], train[target], val[cols], val[target]

    mlflow.set_tracking_uri(tracking_uri())
    mlflow.set_experiment(p["registry"]["experiment"])

    common_tags = {"git_commit": git_commit(), "data_version": data_version(),
                   "sklearn": sklearn.__version__, "python": platform.python_version(),
                   "seed": str(seed)}
    results, best = [], None
    for name in p["train"]["candidates"]:
        with mlflow.start_run(run_name=name) as run:
            mlflow.set_tags(common_tags | {"candidate": name})
            mlflow.log_params({"model": name, **{f"{name}.{k}": v for k, v in p["train"].get(name, {}).items()},
                               "class_weight": p["train"]["class_weight"],
                               "n_train": len(X_tr), "features": ",".join(cols)})
            pipe = Pipeline([("prep", build_preprocessor()), ("clf", make_estimator(name, p))])
            t0 = time.perf_counter()
            pipe.fit(X_tr, y_tr)
            fit_s = time.perf_counter() - t0
            m = score(pipe, X_va, y_va, classes)
            m["fit_seconds"] = fit_s
            mlflow.log_metrics({f"val_{k}": v for k, v in m.items()})
            log.info("%-14s val F1-macro=%.4f recall(high)=%.4f AUC=%.4f (%.1fs)",
                     name, m["f1_macro"], m["recall_high"], m["auc_ovr_macro"], fit_s)
            results.append({"model": name, "run_id": run.info.run_id, **m})
            if best is None or m[p["train"]["primary_metric"]] > best[1][p["train"]["primary_metric"]]:
                best = (name, m, pipe, run.info.run_id)

    name, m, pipe, run_id = best
    log.info("Meilleur modèle : %s (F1-macro val = %.4f)", name, m["f1_macro"])

    # Journalisation du modèle retenu + enregistrement dans le registre
    with mlflow.start_run(run_id=run_id):
        sig = infer_signature(X_va.head(200), pipe.predict_proba(X_va.head(200)))
        info = mlflow.sklearn.log_model(pipe, name="model", signature=sig,
                                        serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
                                        input_example=X_va.head(3),
                                        registered_model_name=p["registry"]["model_name"])
        mlflow.set_tag("selected", "true")

    client = mlflow.MlflowClient()
    version = info.registered_model_version
    client.set_registered_model_alias(p["registry"]["model_name"], "candidate", version)
    client.set_model_version_tag(p["registry"]["model_name"], version, "model_type", name)
    client.set_model_version_tag(p["registry"]["model_name"], version, "data_version", common_tags["data_version"])

    path("models").mkdir(exist_ok=True)
    joblib.dump(pipe, path("models/model.joblib"))
    meta = {"model_name": p["registry"]["model_name"], "version": int(version), "model_type": name,
            "run_id": run_id, "classes": list(pipe.classes_), "features": cols,
            "val_metrics": m, **common_tags,
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    path("models/model_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    path("reports/model_comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
