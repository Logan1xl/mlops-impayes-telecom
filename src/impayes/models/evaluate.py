"""Étape « evaluate » : évaluation sur le jeu de test + quality gate.

- métriques : accuracy, précision, rappel, F1 (macro et par classe),
  AUC one-vs-rest, matrice de confusion, latence d'inférence ;
- figures dans reports/figures ;
- porte de qualité : seuils absolus (params.yaml) + non-régression vs le
  modèle actuellement en production (alias MLflow « production »).
Si la porte est franchie, la version reçoit l'alias « staging ».
"""
from __future__ import annotations

import json
import logging
import sys
import time

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from impayes.config import load_params, path, tracking_uri  # noqa: E402
from impayes.features.build_features import input_columns  # noqa: E402
from impayes.plotting import PALETTE, style_axes, use_report_style  # noqa: E402

use_report_style()

log = logging.getLogger("impayes.evaluate")


def compute_metrics(model, X: pd.DataFrame, y: pd.Series, classes: list[str]) -> dict:
    pred = model.predict(X)
    proba = model.predict_proba(X)
    order = list(model.classes_)
    return {
        "n_test": int(len(y)),
        "accuracy": accuracy_score(y, pred),
        "precision_macro": precision_score(y, pred, average="macro"),
        "recall_macro": recall_score(y, pred, average="macro"),
        "f1_macro": f1_score(y, pred, average="macro"),
        "f1_weighted": f1_score(y, pred, average="weighted"),
        "recall_high": recall_score(y, pred, labels=["high"], average="macro"),
        "precision_high": precision_score(y, pred, labels=["high"], average="macro"),
        "auc_ovr_macro": roc_auc_score(y, proba, multi_class="ovr", average="macro", labels=order),
        "per_class": classification_report(y, pred, labels=classes, output_dict=True),
        "confusion_matrix": {"labels": classes,
                             "matrix": confusion_matrix(y, pred, labels=classes).tolist()},
    }


def latency_benchmark(model, X: pd.DataFrame, n: int = 300) -> dict:
    rows = X.sample(n, random_state=0)
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        model.predict_proba(rows.iloc[[i]])
        times.append((time.perf_counter() - t0) * 1000)
    return {"p50_ms": float(np.percentile(times, 50)), "p95_ms": float(np.percentile(times, 95)),
            "mean_ms": float(np.mean(times))}


def plot_confusion(cm: np.ndarray, labels: list[str], out) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    norm = cm / cm.sum(axis=1, keepdims=True)
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{cm[i, j]:,}\n{norm[i, j]:.0%}".replace(",", " "), ha="center", va="center",
                    fontsize=10, color="white" if norm[i, j] > 0.55 else "#1f2937")
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Classe prédite")
    ax.set_ylabel("Classe réelle")
    ax.set_title("Matrice de confusion (jeu de test)", loc="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_roc(model, X, y, out) -> None:
    proba = model.predict_proba(X)
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    for k, cls in enumerate(model.classes_):
        fpr, tpr, _ = roc_curve((y == cls).astype(int), proba[:, k])
        auc = roc_auc_score((y == cls).astype(int), proba[:, k])
        ax.plot(fpr, tpr, color=PALETTE[cls], lw=2, label=f"{cls} (AUC = {auc:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="#9ca3af", lw=1)
    ax.set_xlabel("Taux de faux positifs")
    ax.set_ylabel("Taux de vrais positifs")
    ax.set_title("Courbes ROC one-vs-rest", loc="left", fontsize=12, fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_importance(model, X, y, out) -> dict:
    sample = X.sample(min(6000, len(X)), random_state=1)
    ys = y.loc[sample.index]
    r = permutation_importance(model, sample, ys, scoring="f1_macro", n_repeats=4, random_state=1, n_jobs=1)
    imp = pd.Series(r.importances_mean, index=X.columns).sort_values()
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.barh(imp.index, imp.values, color=PALETTE["primary"])
    ax.set_xlabel("Baisse du F1-macro quand la variable est permutée")
    ax.set_title("Importance des variables (permutation)", loc="left", fontsize=12, fontweight="bold")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return imp.round(5).to_dict()


def plot_comparison(results: list[dict], out) -> None:
    df = pd.DataFrame(results).set_index("model")
    names = {"logreg": "Régression\nlogistique", "random_forest": "Random\nForest",
             "hist_gbm": "Gradient\nBoosting"}
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    x = np.arange(len(df))
    w = 0.26
    for i, (col, lab, colr) in enumerate([("f1_macro", "F1-macro", PALETTE["primary"]),
                                          ("recall_high", "Rappel « high »", PALETTE["high"]),
                                          ("auc_ovr_macro", "AUC OvR", PALETTE["muted"])]):
        bars = ax.bar(x + (i - 1) * w, df[col], w, label=lab, color=colr)
        ax.bar_label(bars, fmt="%.3f", fontsize=7.5, padding=2)
    ax.set_xticks(x, [names.get(m, m) for m in df.index])
    ax.set_ylim(0, 1.05)
    ax.set_title("Comparaison des candidats (validation)", loc="left", fontsize=12, fontweight="bold")
    ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=8.5)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def production_f1(client, model_name: str) -> float | None:
    try:
        mv = client.get_model_version_by_alias(model_name, "production")
        f1 = mv.tags.get("test_f1_macro")
        return float(f1) if f1 else None
    except Exception:
        return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = load_params()
    target, classes = p["data"]["target"], p["data"]["classes"]
    test = pd.read_parquet(path("data/processed/test.parquet"))
    X, y = test[input_columns()], test[target]
    model = joblib.load(path("models/model.joblib"))
    meta = json.loads(path("models/model_metadata.json").read_text())

    figs = path("reports/figures")
    figs.mkdir(parents=True, exist_ok=True)
    m = compute_metrics(model, X, y, classes)
    m["latency"] = latency_benchmark(model, X)
    plot_confusion(np.array(m["confusion_matrix"]["matrix"]), classes, figs / "confusion_matrix.png")
    plot_roc(model, X, y, figs / "roc_curves.png")
    m["permutation_importance"] = plot_importance(model, X, y, figs / "feature_importance.png")
    comp_path = path("reports/model_comparison.json")
    if comp_path.exists():
        plot_comparison(json.loads(comp_path.read_text()), figs / "model_comparison.png")

    # ----- Quality gate -----
    v = p["validation"]
    mlflow.set_tracking_uri(tracking_uri())
    client = mlflow.MlflowClient()
    prod = production_f1(client, p["registry"]["model_name"])
    gate = {
        "f1_macro >= min": m["f1_macro"] >= v["min_f1_macro"],
        "recall_high >= min": m["recall_high"] >= v["min_recall_high"],
        "latency_p95 <= max": m["latency"]["p95_ms"] <= v["max_latency_ms_p95"],
        "no_regression_vs_production": prod is None or m["f1_macro"] >= prod - v["max_regression_vs_production"],
    }
    m["quality_gate"] = {"checks": gate, "production_f1": prod, "passed": all(gate.values())}
    m["model"] = {k: meta[k] for k in ("model_name", "version", "model_type", "run_id", "data_version", "git_commit")}

    path("reports/metrics.json").write_text(json.dumps(m, indent=2, default=float), encoding="utf-8")
    summary = {k: round(float(m[k]), 4) for k in ("accuracy", "f1_macro", "recall_high", "precision_high", "auc_ovr_macro")}
    summary |= {"latency_p95_ms": round(m["latency"]["p95_ms"], 2), "quality_gate": m["quality_gate"]["passed"]}
    path("reports/metrics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with mlflow.start_run(run_id=meta["run_id"]):
        mlflow.log_metrics({f"test_{k}": float(m[k]) for k in
                            ("accuracy", "precision_macro", "recall_macro", "f1_macro", "recall_high", "auc_ovr_macro")})
        mlflow.log_metric("test_latency_p95_ms", m["latency"]["p95_ms"])
        for f in figs.glob("*.png"):
            mlflow.log_artifact(str(f), artifact_path="figures")

    name, version = p["registry"]["model_name"], str(meta["version"])
    client.set_model_version_tag(name, version, "test_f1_macro", f"{m['f1_macro']:.4f}")
    client.set_model_version_tag(name, version, "quality_gate", "passed" if m["quality_gate"]["passed"] else "failed")
    log.info("Test : F1-macro=%.4f | rappel(high)=%.4f | AUC=%.4f | p95=%.1f ms",
             m["f1_macro"], m["recall_high"], m["auc_ovr_macro"], m["latency"]["p95_ms"])
    for k, ok in gate.items():
        log.info("  gate %-32s %s", k, "OK" if ok else "ÉCHEC")
    if not m["quality_gate"]["passed"]:
        log.error("Quality gate en échec : le modèle n'est PAS promu.")
        sys.exit(1)
    client.set_registered_model_alias(name, "staging", version)
    log.info("Version %s promue en STAGING.", version)


if __name__ == "__main__":
    main()
