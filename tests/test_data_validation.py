"""Tests du contrat de données (étape validate)."""
from impayes.data.validate import run_checks


def _blocking_failures(checks):
    return [c.name for c in checks if c.blocking and not c.passed]


def test_valid_dataset_passes(sample_df):
    assert _blocking_failures(run_checks(sample_df)) == []


def test_missing_column_is_blocking(sample_df):
    df = sample_df.drop(columns=["late_payment_count"])
    assert "colonnes_attendues" in _blocking_failures(run_checks(df))


def test_out_of_range_value_is_blocking(sample_df):
    df = sample_df.copy()
    df.loc[0, "payment_consistency_score"] = 1.7
    assert "plage_payment_consistency_score" in _blocking_failures(run_checks(df))


def test_unknown_target_class_is_blocking(sample_df):
    df = sample_df.copy()
    df.loc[0, "default_risk"] = "very_high"
    assert "domaine_default_risk" in _blocking_failures(run_checks(df))


def test_missing_values_are_blocking(sample_df):
    df = sample_df.copy()
    df.loc[:10, "tenure_months"] = None
    assert "pas_de_valeurs_manquantes" in _blocking_failures(run_checks(df))


def test_credit_rating_rule_matches_score(sample_df):
    """Règle observée sur le jeu réel : poor <500 <= fair <650 <= good <800 <= excellent."""
    bad = sample_df[(sample_df.credit_score >= 800) & (sample_df.credit_rating != "excellent")]
    assert bad.empty
