import pandas as pd
import pytest


@pytest.fixture(scope="session")
def sample_df() -> pd.DataFrame:
    """Petit échantillon de même schéma que le jeu réel (aucun accès réseau)."""
    from impayes.data.synthetic import generate
    return generate(20_000, seed=7)
