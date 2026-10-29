"""Étape « validate » : contrôle qualité du jeu brut (data contract).

Chaque règle produit un résultat PASS/FAIL. Une règle « bloquante » en
échec arrête le pipeline (code de sortie 1) : on n'entraîne jamais un
modèle sur des données qui violent le contrat.
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass

import pandas as pd

from impayes.config import load_params, path

log = logging.getLogger("impayes.validate")

EXPECTED_SCHEMA: dict[str, str] = {
    "customer_id": "object", "phone_number": "object", "operator": "object",
    "assessment_date": "datetime", "credit_score": "int", "credit_rating": "object",
    "tenure_months": "int", "avg_monthly_spend_ngn": "float",
    "recharge_frequency_per_month": "int", "payment_consistency_score": "float",
    "late_payment_count": "int", "account_type": "object", "loan_eligibility": "bool",
    "max_loan_amount_ngn": "float", "default_risk": "object",
}

RANGES: dict[str, tuple[float, float]] = {
    "tenure_months": (1, 120),
    "avg_monthly_spend_ngn": (0, 1_000_000),
    "recharge_frequency_per_month": (0, 31),
    "payment_consistency_score": (0, 1),
    "late_payment_count": (0, 50),
    "credit_score": (300, 1000),
}

DOMAINS: dict[str, set[str]] = {
    "operator": {"MTN", "Airtel", "Glo", "9mobile"},
    "account_type": {"prepaid", "postpaid"},
    "default_risk": {"low", "medium", "high"},
}


@dataclass
class Check:
    name: str
    passed: bool
    blocking: bool
    detail: str


def _kind(dtype) -> str:
    if pd.api.types.is_bool_dtype(dtype):
        return "bool"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    if pd.api.types.is_integer_dtype(dtype):
        return "int"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    return "object"


def run_checks(df: pd.DataFrame) -> list[Check]:
    checks: list[Check] = []
    missing = sorted(set(EXPECTED_SCHEMA) - set(df.columns))
    checks.append(Check("colonnes_attendues", not missing, True,
                        f"manquantes={missing}" if missing else "15/15 présentes"))

    for col, kind in EXPECTED_SCHEMA.items():
        if col not in df.columns:
            continue
        actual = _kind(df[col].dtype)
        ok = actual == kind or (kind == "float" and actual == "int")
        checks.append(Check(f"type_{col}", ok, kind != "object", f"attendu={kind}, obtenu={actual}"))

    feats = load_params()["features"]
    needed = feats["numeric"] + feats["categorical"] + [load_params()["data"]["target"]]
    nulls = {c: int(df[c].isna().sum()) for c in needed if c in df.columns}
    checks.append(Check("pas_de_valeurs_manquantes", sum(nulls.values()) == 0, True,
                        json.dumps({k: v for k, v in nulls.items() if v})))

    for col, (lo, hi) in RANGES.items():
        if col in df.columns:
            bad = int(((df[col] < lo) | (df[col] > hi)).sum())
            checks.append(Check(f"plage_{col}", bad == 0, col in feats["numeric"],
                                f"[{lo}, {hi}] hors-plage={bad}"))

    for col, dom in DOMAINS.items():
        if col in df.columns:
            unknown = sorted(set(df[col].dropna().unique()) - dom)
            checks.append(Check(f"domaine_{col}", not unknown, True, f"inconnues={unknown}"))

    dup = int(df["customer_id"].duplicated().sum()) if "customer_id" in df else 0
    checks.append(Check("unicite_customer_id", dup == 0, False, f"doublons={dup}"))

    if "default_risk" in df:
        share = df["default_risk"].value_counts(normalize=True).round(4).to_dict()
        minority = min(share.values()) if share else 0
        checks.append(Check("equilibre_classes", minority >= 0.05, False,
                            f"proportions={share}"))

    checks.append(Check("volume_minimal", len(df) >= 10_000, True, f"lignes={len(df)}"))
    return checks


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = load_params()
    df = pd.read_parquet(path(p["data"]["raw_path"]))
    checks = run_checks(df)
    report = {"rows": len(df), "checks": [asdict(c) for c in checks],
              "passed": all(c.passed or not c.blocking for c in checks)}
    out = path("reports/data_validation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for c in checks:
        log.info("%-5s %-38s %s", "PASS" if c.passed else ("FAIL" if c.blocking else "WARN"), c.name, c.detail)
    if not report["passed"]:
        log.error("Validation des données en échec : pipeline arrêté.")
        sys.exit(1)


if __name__ == "__main__":
    main()
