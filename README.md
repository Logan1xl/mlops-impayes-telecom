# MLOps — Prédiction des impayés télécom (`default_risk`)

**CC1 · Machine Learning et Modélisation des Données · Dr KUATE Alain François**
EADL5 / JA — Institut Universitaire de la Côte — Normale Semestre I (2026-2027)
Groupe : **MBONGO BOLLO Jarle Wulfrid** · **DONGMO WOZE Junior**

Ce dépôt industrialise un modèle de classification du risque d'impayé (low / medium / high) sur le jeu
[Telecom Credit Scoring Data (Nigeria)](https://huggingface.co/datasets/electricsheepafrica/africa-synth-telecom-telecom-credit-scoring-data-nigeria) :
données validées et versionnées (DVC), entraînement suivi (MLflow), quality gate, registre de modèles,
API FastAPI conteneurisée (Docker), pipelines CI/CD/CT (GitHub Actions + Prefect) et monitoring
(Prometheus, Grafana, détection de dérive).

Ce README est le **guide d'installation et d'exécution** du projet.

> **Note sur les données** — Sans accès à Hugging Face, `python -m impayes.data.download --allow-synthetic`
> génère une réplique de même schéma (200 000 lignes) pour tester toute la chaîne. Avec le vrai jeu,
> l'étape 5 régénère toutes les métriques et figures.

---

## 0. Prérequis

| Outil | Version | Obligatoire ? |
|---|---|---|
| Python | 3.10 à 3.13 | oui |
| Git | récent | oui |
| Docker Desktop (Compose v2) | récent | pour l'image et la pile de monitoring |
| `make` | — | facultatif (sous Windows, utilisez les commandes Python données à chaque étape) |
| draw.io / [diagrams.net](https://app.diagrams.net) | — | pour modifier les schémas |

Environ 2 Go d'espace disque et une connexion Internet pour le premier téléchargement.

## 1. Récupérer le projet et créer l'environnement

```bash
# Linux / macOS / Git Bash
git clone https://github.com/Logan1xl/mlops-impayes-telecom.git && cd mlops-impayes-telecom
python -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows PowerShell
git clone https://github.com/Logan1xl/mlops-impayes-telecom.git ; cd mlops-impayes-telecom
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:PYTHONUTF8 = "1"          # évite les soucis d'accents dans la console
```

## 2. Installer les dépendances

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

`requirements.txt` contient le strict nécessaire à l'exécution (utilisé par l'image Docker) ;
`requirements-dev.txt` ajoute pytest, ruff, DVC, Prefect, Evidently et Jupyter.

## 3. Télécharger et versionner les données

Le dossier `.dvc/` est déjà configuré (remote local `../dvc-storage`).

```bash
python -m impayes.data.download              # make data   — vrai jeu Hugging Face (≈ 17 Mo, 500 000 lignes)
dvc add data/raw/telecom_credit_scoring_data.parquet
git add data/raw/telecom_credit_scoring_data.parquet.dvc data/raw/.gitignore
git commit -m "data: jeu Telecom Credit Scoring v1"
dvc push                                     # copie les données vers le remote DVC
```

`data/raw/SOURCE.json` indique l'origine des données (`huggingface` ou `synthetic_replica`).
Sans Internet : `python -m impayes.data.download --allow-synthetic` (ou `make data-offline`).

> Remote partagé pour le binôme : `dvc remote add -d gdrive gdrive://<ID_DOSSIER>` (ou S3), puis `dvc push` / `dvc pull`.

## 4. Vérifier le code

```bash
ruff check src tests pipelines               # make lint  — analyse statique
pytest                                       # make test  — 32 tests (données, features, modèle, API, dérive)
```

## 5. Exécuter le pipeline complet

```bash
dvc repro                                    # validate → preprocess → train → evaluate
```

Équivalent sans DVC : `make pipeline`, ou

```bash
python -m impayes.data.validate
python -m impayes.features.build_features
python -m impayes.models.train
python -m impayes.models.evaluate
```

| Étape | Ce qui se passe | Sorties |
|---|---|---|
| validate | contrat de données (schéma, plages, domaines) ; arrêt si règle bloquante | `reports/data_validation.json` |
| preprocess | sélection des variables, split stratifié 70/10/20, jeu de référence | `data/processed/`, `data/reference/` |
| train | LogReg, RandomForest, HistGBM tracés dans MLflow ; meilleur → registre `@candidate` | `models/model.joblib`, `reports/model_comparison.json` |
| evaluate | métriques test, figures, latence, **quality gate** → alias `@staging` | `reports/metrics.json`, `reports/figures/` |

```bash
dvc metrics show                             # résumé des métriques
dvc dag                                      # graphe du pipeline
```

## 6. Explorer les expériences et promouvoir le modèle

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000      # make mlflow-ui → http://localhost:5000
python -m impayes.models.registry list
python -m impayes.models.registry promote --version 1 --to production --approved-by "DONGMO WOZE Junior"
python -m impayes.models.registry rollback --approved-by "DONGMO WOZE Junior"   # si besoin
```

Chaque promotion est tracée dans `reports/registry_audit.jsonl`. Le tableau des runs est aussi exporté dans
`reports/mlflow_experiments.md` / `.csv`.

## 7. Lancer l'API

```bash
uvicorn impayes.api.main:app --reload --port 8000                  # make api
```

Ouvrir **http://localhost:8000/docs** (Swagger). Exemple :

```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{
  "tenure_months": 7, "avg_monthly_spend_ngn": 48856.01, "recharge_frequency_per_month": 5,
  "payment_consistency_score": 0.6, "late_payment_count": 9, "operator": "Glo",
  "account_type": "prepaid", "customer_ref": "DEMO-1"}'
```

PowerShell : `Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body '{...}'`

| Endpoint | Rôle |
|---|---|
| `POST /predict`, `POST /predict/batch` | prédiction unitaire / par lot (≤ 1 000) |
| `POST /feedback` | issue réelle (impayé constaté) pour le concept drift |
| `GET /health`, `GET /model-info` | disponibilité, version du modèle |
| `GET /metrics` | métriques Prometheus |
| `POST /admin/reload` | recharge le modèle (en-tête `x-admin-token` = `ADMIN_TOKEN`) |

Par défaut l'API charge `models/model.joblib`. Pour lire le registre : `MODEL_SOURCE=registry`.
Chaque prédiction est journalisée (sans donnée personnelle) dans `data/production/predictions.jsonl`.

## 8. Docker et pile de monitoring

```bash
docker build -f docker/Dockerfile.api -t impayes-api:latest .      # make docker-build
docker run -p 8000:8000 impayes-api:latest

docker compose up -d --build                                       # make up
```

| Service | URL |
|---|---|
| API | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |
| Prometheus (+ alertes) | http://localhost:9090 |
| Grafana (admin / admin) | http://localhost:3000 → dossier *MLOps* → « Impayés télécom — Monitoring » |

Générer un peu de trafic pour voir les courbes :

```bash
./scripts/smoke_test.sh http://localhost:8000
for i in $(seq 1 200); do ./scripts/smoke_test.sh http://localhost:8000 >/dev/null; done
```

Arrêt : `docker compose down`.

## 9. Monitoring de dérive

```bash
python -m impayes.monitoring.run simulate    # make monitor-sim : scénario de 12 semaines (inflation puis crise)
python -m impayes.monitoring.run batch       # make monitor     : analyse des prédictions réellement servies
```

Ouvrir `reports/monitoring/dashboard.html` dans un navigateur. Le mode `batch` renvoie le code **3** quand la
règle de décision demande un réentraînement (utilisé par le workflow CT).

Continuous Training en local (Prefect facultatif) :

```bash
python pipelines/ct_flow.py            # réentraîne seulement si dérive confirmée
python pipelines/ct_flow.py --force    # force le cycle complet
```

## 10. CI/CD/CT sur GitHub

1. Créer un dépôt GitHub et pousser : `git remote add origin <url> && git push -u origin main`.
2. Les workflows de `.github/workflows/` démarrent automatiquement :
   - **ci.yml** (push / PR) : ruff, pytest, pipeline, quality gate, build Docker, scan Trivy, métriques en commentaire de PR ;
   - **cd.yml** (tag `model-v*` ou lancement manuel) : image GHCR, staging, canary, promotion ;
   - **ct.yml** (tous les jours à 03:00 UTC) : monitoring → réentraînement → PR de promotion.
3. Pour le CD/CT réels : secret `MLFLOW_TRACKING_URI` (serveur MLflow), environnements GitHub `staging` et
   `production` (avec *required reviewers* = approbation humaine), variables `STAGING_URL` et `PROMETHEUS_URL`,
   et un cluster Kubernetes (`deploy/k8s/api.yaml`). Sans cluster, la CI fonctionne entièrement seule.

## 11. Modifier les schémas

- Ouvrir `docs/architecture.drawio` et `docs/pipeline_ci_cd_ct.drawio` dans draw.io / diagrams.net
  (Fichier → Ouvrir) : chaque boîte, texte, flèche et pictogramme est modifiable ; export PNG/PDF possible.
- Ou les régénérer depuis le code (mêmes coordonnées que les fichiers .drawio) :
  `pip install cairosvg && cd docs/diagram && python architecture.py && python figures.py`
  (`figures.py` produit aussi des figures explicatives dans `docs/figures/`).
- Les pictogrammes sont des icônes génériques Font Awesome (licence CC BY 4.0), exportées par `export_icons.js`.

## Arborescence

```
mlops-impayes-telecom/
├── params.yaml · dvc.yaml · Makefile · pyproject.toml · requirements*.txt
├── src/impayes/
│   ├── config.py · plotting.py
│   ├── data/          download.py · validate.py · synthetic.py
│   ├── features/      build_features.py
│   ├── models/        train.py · evaluate.py · registry.py
│   ├── monitoring/    drift.py · run.py
│   └── api/           main.py · schemas.py
├── pipelines/ct_flow.py              orchestration Prefect du CT
├── tests/                            32 tests pytest
├── notebooks/01_eda.ipynb            exploration des données
├── docker/  docker-compose.yml       images API / entraînement, pile locale
├── monitoring/                       Prometheus, règles d'alerte, Grafana (provisioning + dashboard)
├── deploy/k8s/api.yaml               stable + canary + HPA + Ingress
├── scripts/                          deploy.sh · smoke_test.sh · canary_check.sh
├── .github/workflows/                ci.yml · cd.yml · ct.yml
├── docs/                             architecture & pipeline (.drawio/.png/.svg), data_preprocessing.md,
│                                     model_card.md, governance.md, openapi.json, figures/, diagram/ (schémas as code)
├── models/                           généré : model.joblib + model_metadata.json
└── reports/                          généré : métriques, figures, monitoring/dashboard.html
```

## Dépannage

| Symptôme | Solution |
|---|---|
| `ModuleNotFoundError: impayes` | `pip install -e .` dans l'environnement activé |
| Téléchargement Hugging Face impossible | vérifier la connexion / proxy, ou placer le fichier `.parquet` dans `data/raw/` |
| `ERROR: ... is already tracked by SCM` (DVC) | ne pas versionner dans Git un fichier listé en `outs` de `dvc.yaml` |
| Quality gate en échec (code 1) | normal si le modèle est sous les seuils : voir `reports/metrics.json` et `params.yaml` |
| Port 8000 / 5000 déjà utilisé | changer `--port` ou les ports dans `docker-compose.yml` |
| `make` introuvable (Windows) | utiliser les commandes `python -m …` indiquées à chaque étape |
