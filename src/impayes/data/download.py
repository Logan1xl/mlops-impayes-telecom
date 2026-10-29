"""Étape DVC « ingest » : récupère le jeu de données brut.

Ordre de tentative :
1. fichier déjà présent dans data/raw (ex. récupéré via `dvc pull`) ;
2. téléchargement depuis Hugging Face (huggingface_hub, puis URL directe) ;
3. en dernier recours, réplique synthétique de même schéma (--allow-synthetic),
   clairement signalée dans data/raw/SOURCE.json.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from impayes.config import load_params, path
from impayes.data import synthetic

log = logging.getLogger("impayes.ingest")


def _write_source(kind: str, detail: str, n_rows: int) -> None:
    meta = {"source": kind, "detail": detail, "rows": n_rows,
            "retrieved_at": datetime.now(timezone.utc).isoformat()}
    out = path("data/raw/SOURCE.json")
    out.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Source des données : %s", meta)


def _try_hf_hub(repo: str, filename: str, dest) -> bool:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        return False
    try:
        local = hf_hub_download(repo_id=repo, filename=filename, repo_type="dataset")
        shutil.copy(local, dest)
        return True
    except Exception as exc:  # réseau, quota, etc.
        log.warning("huggingface_hub indisponible : %s", exc)
        return False


def _try_direct(repo: str, filename: str, dest) -> bool:
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{filename}"
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return True
    except Exception as exc:
        log.warning("Téléchargement direct impossible (%s) : %s", url, exc)
        return False


def ingest(allow_synthetic: bool = False, force: bool = False) -> pd.DataFrame:
    p = load_params()
    dest = path(p["data"]["raw_path"])
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not force:
        df = pd.read_parquet(dest)
        log.info("Fichier brut déjà présent (%d lignes) : %s", len(df), dest)
        return df

    repo, filename = p["data"]["hf_repo"], p["data"]["hf_file"]
    if _try_hf_hub(repo, filename, dest) or _try_direct(repo, filename, dest):
        df = pd.read_parquet(dest)
        _write_source("huggingface", f"{repo}/{filename}", len(df))
        return df

    if not allow_synthetic:
        raise SystemExit(
            "Impossible de télécharger le jeu Hugging Face. Placez le fichier "
            f"{filename} dans data/raw/ ou relancez avec --allow-synthetic.")

    n = p["data"]["fallback_sample_rows"]
    log.warning("Génération d'une RÉPLIQUE SYNTHÉTIQUE (%d lignes)", n)
    df = synthetic.generate(n, seed=p["project"]["seed"])
    df.to_parquet(dest, index=False)
    _write_source("synthetic_replica", "impayes.data.synthetic.generate", len(df))
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-synthetic", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    df = ingest(allow_synthetic=args.allow_synthetic, force=args.force)
    print(f"OK : {len(df):,} lignes, {df.shape[1]} colonnes")


if __name__ == "__main__":
    main()
