"""Réplique synthétique du jeu « Telecom Credit Scoring Data (Nigeria) ».

Utilisée UNIQUEMENT quand le vrai fichier ne peut pas être téléchargé
(machine hors ligne, CI sans accès réseau, tests unitaires). Le schéma
(15 colonnes, types, domaines de valeurs, règles credit_rating /
loan_eligibility) reproduit celui observé sur Hugging Face. Les
relations entre variables sont plausibles mais NE SONT PAS celles du
vrai jeu : les métriques obtenues sur la réplique ne doivent pas être
présentées comme résultats finaux.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

OPERATORS = ["MTN", "Airtel", "Glo", "9mobile"]
OPERATOR_P = [0.40, 0.30, 0.18, 0.12]
PREFIXES = {"MTN": ["803", "806", "703", "706", "813", "816", "903", "906"],
            "Airtel": ["802", "808", "701", "708", "812", "901", "902"],
            "Glo": ["805", "807", "705", "815", "811", "905"],
            "9mobile": ["809", "817", "818", "909", "908"]}


def rating_from_score(score: np.ndarray) -> np.ndarray:
    """Règle observée : <500 poor, 500-649 fair, 650-799 good, >=800 excellent."""
    return np.select([score < 500, score < 650, score < 800],
                     ["poor", "fair", "good"], default="excellent")


def generate(n: int = 200_000, seed: int = 42, spend_shift: float = 1.0,
             late_shift: float = 0.0, concept_shift: float = 0.0) -> pd.DataFrame:
    """Génère n lignes.

    spend_shift   : multiplicateur des dépenses (simule l'inflation -> data drift)
    late_shift    : décalage du nombre moyen de retards (data drift)
    concept_shift : modifie la relation features -> cible (concept drift)
    """
    rng = np.random.default_rng(seed)
    operator = rng.choice(OPERATORS, size=n, p=OPERATOR_P)
    account_type = rng.choice(["prepaid", "postpaid"], size=n, p=[0.85, 0.15])
    tenure = rng.integers(1, 121, size=n)
    spend = np.clip(rng.uniform(500, 50_000, size=n) * spend_shift, 500, 50_000 * spend_shift)
    recharge = rng.integers(1, 31, size=n)
    consistency = np.round(rng.uniform(0, 1, size=n), 2)
    # Retards : majorité 0-2, queue jusqu'à 10 ; dépend un peu de l'ancienneté
    base_late = rng.poisson(1.1 + late_shift, size=n)
    heavy = rng.random(n) < (0.18 - 0.0008 * tenure)
    late = np.clip(np.where(heavy, rng.integers(3, 11, size=n), base_late), 0, 10)

    noise = rng.normal(0, 55, size=n)
    score = (380 + 3.6 * tenure + 0.0075 * spend / spend_shift - 42 * late
             + 60 * consistency + 2.0 * recharge + noise)
    score = np.clip(np.round(score), 300, 1000).astype(int)
    rating = rating_from_score(score)
    eligible = score >= 650
    max_loan = np.where(eligible, np.round(spend * rng.uniform(1.0, 2.8, size=n), 2), 0.0)
    max_loan = np.clip(max_loan, 0, 150_000)

    # Risque latent. Le concept_shift renforce l'effet des retards et
    # réduit l'effet protecteur de l'ancienneté (crise économique). Les
    # seuils de classe sont calculés sur le risque « de référence » (sans
    # concept_shift) afin qu'une dérive de concept modifie réellement la
    # proportion de clients à risque élevé.
    eps = rng.logistic(0, 0.55, size=n)

    def latent(c: float) -> np.ndarray:
        return (0.55 * (1 + c) * late
                - 0.012 * (1 - c) * tenure
                - 0.000025 * spend / spend_shift
                - 0.9 * consistency
                - 0.025 * recharge
                + (account_type == "postpaid") * 0.25
                + eps)

    q_low, q_high = np.quantile(latent(0.0), [0.55, 0.78])
    z = latent(concept_shift)
    risk = np.select([z < q_low, z < q_high], ["low", "medium"], default="high")

    ids = rng.choice(np.arange(1_000_000, 9_999_999), size=n, replace=False)
    prefixes = np.array([rng.choice(PREFIXES[o]) for o in operator])
    phones = np.char.add(np.char.add("+234", prefixes), rng.integers(1_000_000, 9_999_999, size=n).astype(str))

    return pd.DataFrame({
        "customer_id": np.char.add("CUST", ids.astype(str)),
        "phone_number": phones,
        "operator": operator,
        "assessment_date": pd.Timestamp("2025-09-30"),
        "credit_score": score,
        "credit_rating": rating,
        "tenure_months": tenure,
        "avg_monthly_spend_ngn": np.round(spend, 2),
        "recharge_frequency_per_month": recharge,
        "payment_consistency_score": consistency,
        "late_payment_count": late.astype(int),
        "account_type": account_type,
        "loan_eligibility": eligible,
        "max_loan_amount_ngn": max_loan,
        "default_risk": risk,
    })

