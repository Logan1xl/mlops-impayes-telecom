#!/usr/bin/env python
"""Export des artefacts de la démo (app web autonome, sans installation).

Produit :
  demo/assets/model.json    — scaler, OHE, coefficients LogReg (inférence 100 % JS)
  demo/assets/metrics.json  — métriques test, comparaison candidats, quality gate
  demo/assets/trace.json    — traces MLflow (runs, registre, audit) depuis mlflow.db

Régénérer après `dvc repro` :
  python scripts/export_demo_assets.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "demo" / "assets"


def export_model() -> dict:
    model = joblib.load(ROOT / "models/model.joblib")
    meta = json.loads((ROOT / "models/model_metadata.json").read_text())
    prep = model.named_steps["prep"]
    ct = prep.named_steps["columns"]
    numeric = ["tenure_months", "avg_monthly_spend_ngn", "recharge_frequency_per_month",
               "payment_consistency_score", "late_payment_count",
               "spend_per_recharge", "late_rate", "log_spend", "is_new_customer"]
    scaler = ct.named_transformers_["num"]
    ohe = ct.named_transformers_["cat"]
    clf = model.named_steps["clf"]
    if clf.__class__.__name__ != "LogisticRegression":
        # La démo autonome n'embarque que les coefficients LogReg.
        # On écrit un modèle.js « unsupported » : l'app bascule alors en mode
        # connecté (API) — la régénération du reste reste possible sans casser.
        data = {
            "format": "impayes-js/1",
            "unsupported": True,
            "model_class": clf.__class__.__name__,
            "model_name": meta.get("model_name", "impayes-default-risk"),
            "model_version": meta.get("version"),
            "model_type": meta.get("model_type"),
        }
        return data
    data = {
        "format": "impayes-js/1",
        "model_name": meta.get("model_name", "impayes-default-risk"),
        "model_version": meta.get("version"),
        "model_type": meta.get("model_type"),
        "trained_at": meta.get("trained_at"),
        "data_version": meta.get("data_version"),
        "git_commit": meta.get("git_commit"),
        "classes": [str(c) for c in clf.classes_],
        "numeric": numeric,
        "scaler_mean": [float(v) for v in scaler.mean_],
        "scaler_scale": [float(v) for v in scaler.scale_],
        "ohe_operator": [str(c) for c in ohe.categories_[0]],
        "ohe_account_type": [str(c) for c in ohe.categories_[1]],
        "coef": [[float(v) for v in row] for row in clf.coef_],
        "intercept": [float(v) for v in clf.intercept_],
    }
    return data


def export_metrics() -> dict:
    out = {}
    for name, key in [("metrics.json", "test"), ("model_comparison.json", "comparison"),
                      ("metrics_summary.json", "summary"), ("split_stats.json", "split")]:
        p = ROOT / "reports" / name
        if p.exists():
            out[key] = json.loads(p.read_text())
    return out


def write_js(path: Path, var: str, data: dict) -> None:
    path.write_text(f"window.{var} = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
                    encoding="utf-8")


def export_trace() -> dict:
    db = ROOT / "mlflow.db"
    out: dict = {"experiment": "impayes-default-risk", "runs": [], "audit": [], "registry": []}
    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        # Runs + paramètres + métriques + tags (schéma MLflow 3.x)
        row = con.execute("SELECT experiment_id FROM experiments WHERE name=?",
                          (out["experiment"],)).fetchone()
        if row:
            eid = row[0]
            runs = con.execute(
                "SELECT run_uuid, name, status, start_time, end_time FROM runs WHERE experiment_id=?",
                (eid,)).fetchall()
            for r in runs:
                ruid = r["run_uuid"]
                params = {row["key"]: row["value"] for row in con.execute(
                    "SELECT key, value FROM params WHERE run_uuid=?", (ruid,))}
                metrics = {row["key"]: row["value"] for row in con.execute(
                    "SELECT key, value FROM metrics WHERE run_uuid=?", (ruid,))}
                tags = {row["key"]: row["value"] for row in con.execute(
                    "SELECT key, value FROM tags WHERE run_uuid=?", (ruid,))}
                out["runs"].append({
                    "run_id": ruid,
                    "name": r["name"] or params.get("model", "?"),
                    "status": r["status"],
                    "start_time": r["start_time"],
                    "model": params.get("model"),
                    "git_commit": tags.get("git_commit"),
                    "data_version": tags.get("data_version"),
                    "selected": tags.get("selected") == "true",
                    "params": params,
                    "metrics": metrics,
                    "tags": {k: v for k, v in tags.items()
                             if not k.startswith(("mlflow.log-model", "mlflow"))},
                })
            out["runs"].sort(key=lambda x: x["start_time"] or 0)
        con.close()
    audit = ROOT / "reports" / "registry_audit.jsonl"
    if audit.exists():
        for line in audit.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out["audit"].append(json.loads(line))
    meta = ROOT / "models" / "model_metadata.json"
    if meta.exists():
        m = json.loads(meta.read_text())
        out["registry"].append({k: m.get(k) for k in
                                ("model_name", "version", "model_type", "run_id",
                                 "data_version", "git_commit", "trained_at")})
    manifest = ROOT / "dvc.lock"
    if manifest.exists():
        out["pipeline_lock"] = True
    return out


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    model = export_model()
    metrics = export_metrics()
    trace = export_trace()
    (ASSETS / "model.json").write_text(json.dumps(model, indent=1), encoding="utf-8")
    (ASSETS / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (ASSETS / "trace.json").write_text(json.dumps(trace, indent=1), encoding="utf-8")
    # Variantes JS (window.*) pour fonctionner hors-ligne via file:// (fetch bloqué)
    write_js(ASSETS / "model.js", "MODEL", model)
    write_js(ASSETS / "metrics.js", "METRICS", metrics)
    write_js(ASSETS / "trace.js", "TRACE", trace)
    print(f"model.json      : {ASSETS / 'model.json'} ({len(json.dumps(model))} o) + model.js")
    print(f"metrics.json    : {ASSETS / 'metrics.json'} + metrics.js")
    print(f"trace.json      : {ASSETS / 'trace.json'} ({len(trace['runs'])} runs, "
          f"{len(trace['audit'])} événements d'audit) + trace.js")


if __name__ == "__main__":
    main()
