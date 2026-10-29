"""Orchestration du Continuous Training avec Prefect.

    python pipelines/ct_flow.py                 # exécution immédiate
    prefect deploy pipelines/ct_flow.py:ct_flow --cron "0 3 * * *" -n quotidien

Si Prefect n'est pas installé, le flux s'exécute en séquentiel (mêmes étapes),
ce qui permet de le tester partout. GitHub Actions (ct.yml) est l'alternative
retenue quand on ne veut pas maintenir un serveur Prefect.
"""
from __future__ import annotations

import logging
import subprocess
import sys

try:
    from prefect import flow, task
except ImportError:  # repli sans Prefect
    def task(fn=None, **_):
        return fn if fn else (lambda f: f)

    def flow(fn=None, **_):
        return fn if fn else (lambda f: f)

log = logging.getLogger("ct_flow")
PY = sys.executable


def _run(*args: str) -> int:
    log.info("$ %s", " ".join(args))
    return subprocess.call([PY, "-m", *args])


@task(retries=2, retry_delay_seconds=60)
def check_drift() -> bool:
    """Code 3 = la règle de décision demande un réentraînement."""
    return _run("impayes.monitoring.run", "batch") == 3


@task(retries=2, retry_delay_seconds=300)
def refresh_data() -> None:
    if _run("impayes.data.download", "--force") != 0:
        raise RuntimeError("Ingestion impossible")


@task
def validate_data() -> None:
    if _run("impayes.data.validate") != 0:
        raise RuntimeError("Contrat de données violé : arrêt du CT")


@task
def build_features() -> None:
    _run("impayes.features.build_features")


@task
def train() -> None:
    if _run("impayes.models.train") != 0:
        raise RuntimeError("Échec d'entraînement")


@task
def evaluate_and_gate() -> bool:
    return _run("impayes.models.evaluate") == 0


@flow(name="impayes-continuous-training", log_prints=True)
def ct_flow(force: bool = False) -> str:
    if not (force or check_drift()):
        return "Aucune dérive bloquante : pas de réentraînement."
    refresh_data()
    validate_data()
    build_features()
    train()
    if evaluate_and_gate():
        return ("Nouveau modèle en STAGING. Promotion en production après revue humaine : "
                "python -m impayes.models.registry promote --version <v> --to production --approved-by <nom>")
    return "Quality gate en échec : le modèle de production est conservé."


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(ct_flow(force="--force" in sys.argv))
