"""Chargement centralisé de la configuration (params.yaml)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
PARAMS_PATH = Path(os.getenv("IMPAYES_PARAMS", ROOT / "params.yaml"))

DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


@lru_cache(maxsize=1)
def load_params() -> dict[str, Any]:
    with open(PARAMS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(rel: str) -> Path:
    """Résout un chemin relatif à la racine du projet."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p


def tracking_uri() -> str:
    """URI MLflow : variable d'environnement prioritaire, sinon params.yaml.

    Une URI sqlite relative est ancrée à la racine du projet pour que les
    scripts fonctionnent quel que soit le répertoire courant.
    """
    uri = os.getenv("MLFLOW_TRACKING_URI") or load_params()["registry"]["tracking_uri"]
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        uri = "sqlite:///" + str(ROOT / uri.removeprefix("sqlite:///"))
    return uri
