# ================================================================
#  Raccourcis du projet (Linux / macOS / Git Bash sous Windows)
#  Les commandes Python équivalentes sont données dans le README.
# ================================================================
PY ?= python

.PHONY: help install data data-offline validate features train evaluate pipeline \
        test lint api mlflow-ui monitor-sim monitor promote docker-build up down clean

help:            ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

install:         ## Installe les dépendances + le paquet en mode éditable
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pip install -e .

data:            ## Télécharge le vrai jeu Hugging Face (500 000 lignes)
	$(PY) -m impayes.data.download

data-offline:    ## Sans Internet : génère une réplique synthétique de même schéma
	$(PY) -m impayes.data.download --allow-synthetic

validate:        ## Contrôle qualité des données (data contract)
	$(PY) -m impayes.data.validate

features:        ## Feature engineering + split train/val/test
	$(PY) -m impayes.features.build_features

train:           ## Entraîne et compare les modèles (MLflow)
	$(PY) -m impayes.models.train

evaluate:        ## Évaluation test + quality gate (+ alias staging)
	$(PY) -m impayes.models.evaluate

pipeline: validate features train evaluate  ## Pipeline complet (équivalent dvc repro)

test:            ## Tests unitaires et d'intégration
	$(PY) -m pytest

lint:            ## Analyse statique
	ruff check src tests pipelines

api:             ## Lance l'API en local (http://localhost:8000/docs)
	uvicorn impayes.api.main:app --reload --port 8000

mlflow-ui:       ## Interface MLflow (http://localhost:5000)
	mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000

monitor-sim:     ## Scénario de dérive sur 12 semaines + tableau de bord HTML
	$(PY) -m impayes.monitoring.run simulate

monitor:         ## Analyse des prédictions réellement servies par l'API
	$(PY) -m impayes.monitoring.run batch

promote:         ## Promotion en production : make promote V=1 BY="Nom Prénom"
	$(PY) -m impayes.models.registry promote --version $(V) --to production --approved-by "$(BY)"

docker-build:    ## Construit l'image de l'API
	docker build -f docker/Dockerfile.api -t impayes-api:latest .

up:              ## Démarre API + MLflow + Prometheus + Grafana
	docker compose up -d --build

down:            ## Arrête la pile Docker
	docker compose down

clean:           ## Supprime les artefacts générés (pas les données brutes)
	rm -rf data/processed data/reference reports/figures reports/monitoring mlruns mlflow.db models/model.joblib
