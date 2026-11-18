"""Chargement centralisé de la configuration (params.yaml)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    """Racine du projet.

    Installation éditable (dev) : parents[2] de ce fichier = racine du dépôt.
    Installation dans une image Docker (site-packages, WORKDIR /app) :
    parents[2] n'existe pas côté données -> on retombe sur le répertoire
    courant, où le Dockerfile place params.yaml, models/ et data/.
    """
    pkg_root = Path(__file__).resolve().parents[2]
    if (pkg_root / "params.yaml").exists():
        return pkg_root
    cwd = Path.cwd()
    if (cwd / "params.yaml").exists():
        return cwd
    return pkg_root  # comportement historique (erreur explicite en aval)


ROOT = _repo_root()
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
