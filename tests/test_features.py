"""Tests du feature engineering et du découpage."""
import numpy as np
import pandas as pd

from impayes.features.build_features import (
    ENGINEERED,
    TelecomFeatures,
    build_preprocessor,
    input_columns,
    split_dataset,
)


def test_engineered_features_added(sample_df):
    out = TelecomFeatures().transform(sample_df[input_columns()])
    for col in ENGINEERED:
        assert col in out.columns
    assert np.isfinite(out[ENGINEERED].to_numpy(dtype=float)).all()


def test_no_division_by_zero():
    row = pd.DataFrame([{"tenure_months": 0, "avg_monthly_spend_ngn": 0.0, "recharge_frequency_per_month": 0,
                         "payment_consistency_score": 0.5, "late_payment_count": 3,
                         "operator": "MTN", "account_type": "prepaid"}])
    out = TelecomFeatures().transform(row)
    assert np.isfinite(out[ENGINEERED].to_numpy(dtype=float)).all()


def test_transform_does_not_mutate_input(sample_df):
    X = sample_df[input_columns()].copy()
    before = X.copy()
    TelecomFeatures().transform(X)
    pd.testing.assert_frame_equal(X, before)


def test_unknown_category_is_tolerated(sample_df):
    X = sample_df[input_columns()]
    prep = build_preprocessor().fit(X)
    new = X.head(2).copy()
    new["operator"] = "NouvelOperateur"
    assert prep.transform(new).shape[0] == 2


def test_split_is_stratified_and_disjoint(sample_df):
    s = split_dataset(sample_df)
    total = sum(len(v) for v in s.values())
    assert total == len(sample_df)
    shares = [v["default_risk"].value_counts(normalize=True)["high"] for v in s.values()]
    assert max(shares) - min(shares) < 0.01
    assert set(s["train"].index).isdisjoint(s["test"].index)


def test_pii_and_leaky_columns_excluded():
    cols = input_columns()
    for forbidden in ("customer_id", "phone_number", "credit_score", "loan_eligibility"):
        assert forbidden not in cols
