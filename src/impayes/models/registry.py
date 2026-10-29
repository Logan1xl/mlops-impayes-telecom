"""Gestion du Model Registry MLflow (aliases candidate / staging / production).

Usage :
  python -m impayes.models.registry list
  python -m impayes.models.registry promote --version 3 --to production --approved-by "J. Dongmo"
  python -m impayes.models.registry rollback            # revient à la version précédente
  python -m impayes.models.registry export              # copie la version « production » vers models/
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import joblib
import mlflow

from impayes.config import load_params, path, tracking_uri

ALIASES = ("candidate", "staging", "production", "previous_production")


def _client() -> mlflow.MlflowClient:
    mlflow.set_tracking_uri(tracking_uri())
    return mlflow.MlflowClient()


def _audit(event: dict) -> None:
    """Journal d'audit append-only (qui a promu quoi, quand, pourquoi)."""
    log_file = path("reports/registry_audit.jsonl")
    log_file.parent.mkdir(exist_ok=True)
    event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def list_versions() -> list[dict]:
    c, name = _client(), load_params()["registry"]["model_name"]
    alias_of: dict[str, list[str]] = {}
    rm = c.get_registered_model(name)
    for alias, ver in (rm.aliases or {}).items():
        alias_of.setdefault(str(ver), []).append(alias)
    rows = []
    for mv in sorted(c.search_model_versions(f"name='{name}'"), key=lambda m: int(m.version)):
        rows.append({"version": mv.version, "aliases": alias_of.get(str(mv.version), []),
                     "type": mv.tags.get("model_type"), "test_f1": mv.tags.get("test_f1_macro"),
                     "gate": mv.tags.get("quality_gate"), "run_id": mv.run_id})
    return rows


def promote(version: str, to: str, approved_by: str, reason: str = "") -> None:
    if to not in ("staging", "production"):
        raise SystemExit("--to doit valoir staging ou production")
    c, name = _client(), load_params()["registry"]["model_name"]
    mv = c.get_model_version(name, version)
    if to == "production" and mv.tags.get("quality_gate") != "passed":
        raise SystemExit(f"Refus : la version {version} n'a pas franchi la quality gate.")
    if to == "production":
        try:
            current = c.get_model_version_by_alias(name, "production")
            c.set_registered_model_alias(name, "previous_production", current.version)
        except Exception:
            pass
    c.set_registered_model_alias(name, to, version)
    c.set_model_version_tag(name, version, f"approved_{to}_by", approved_by)
    _audit({"action": "promote", "model": name, "version": version, "to": to,
            "approved_by": approved_by, "reason": reason})
    print(f"Version {version} -> {to} (approuvée par {approved_by})")


def rollback(approved_by: str) -> None:
    c, name = _client(), load_params()["registry"]["model_name"]
    prev = c.get_model_version_by_alias(name, "previous_production")
    cur = c.get_model_version_by_alias(name, "production")
    c.set_registered_model_alias(name, "production", prev.version)
    c.set_registered_model_alias(name, "previous_production", cur.version)
    _audit({"action": "rollback", "model": name, "from": cur.version, "to": prev.version,
            "approved_by": approved_by})
    print(f"Rollback : production {cur.version} -> {prev.version}")


def export(alias: str = "production") -> None:
    """Exporte la version portant l'alias vers models/ (artefact embarqué dans l'image Docker)."""
    c, name = _client(), load_params()["registry"]["model_name"]
    mv = c.get_model_version_by_alias(name, alias)
    model = mlflow.sklearn.load_model(f"models:/{name}@{alias}")
    joblib.dump(model, path("models/model.joblib"))
    meta_path = path("models/model_metadata.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"version": int(mv.version), "alias": alias, "run_id": mv.run_id,
                 "model_type": mv.tags.get("model_type")})
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Exporté : {name} v{mv.version} (@{alias}) -> models/model.joblib")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    pr = sub.add_parser("promote")
    pr.add_argument("--version", required=True)
    pr.add_argument("--to", required=True)
    pr.add_argument("--approved-by", required=True)
    pr.add_argument("--reason", default="")
    rb = sub.add_parser("rollback")
    rb.add_argument("--approved-by", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--alias", default="production")
    a = ap.parse_args()
    if a.cmd == "list":
        for r in list_versions():
            print(f"v{r['version']:>3}  {','.join(r['aliases']) or '-':<32} {r['type'] or '-':<14} "
                  f"F1={r['test_f1'] or '-':<7} gate={r['gate'] or '-'}")
    elif a.cmd == "promote":
        promote(a.version, a.to, a.approved_by, a.reason)
    elif a.cmd == "rollback":
        rollback(a.approved_by)
    else:
        export(a.alias)


if __name__ == "__main__":
    main()
