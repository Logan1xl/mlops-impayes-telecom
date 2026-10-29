# Gouvernance, versioning et auditabilité

## Politique de versioning
| Objet | Outil | Identifiant |
|---|---|---|
| Code, configuration, pipeline | Git (branches `main` / `develop`, PR obligatoires) | commit SHA, tags `model-vX` |
| Données brutes et dérivées | DVC (remote S3 / Google Drive) | hash MD5 dans `*.dvc` et `dvc.lock` |
| Paramètres | `params.yaml` suivi par DVC | inclus dans `dvc.lock` |
| Expériences | MLflow Tracking | `run_id` (params, métriques, figures, environnement) |
| Modèles | MLflow Model Registry | version entière + alias `candidate` / `staging` / `production` / `previous_production` |
| Images de serving | GHCR | `model-<version>-<commit>` |

Versionnement sémantique côté métier : changement de variables ou de cible = version **majeure** (nouveau contrat d'API) ; réentraînement sur données fraîches = version **mineure**.

## Cycle de vie d'un modèle
`candidate` (entraîné) → `staging` (quality gate franchie automatiquement) → `production` (approbation humaine de la Direction du risque + canary réussi) → `previous_production` (conservé pour rollback immédiat) → archivé après 2 versions.

## Gouvernance des données
- Contrat de données exécuté à chaque run (schéma, plages, domaines).
- Minimisation : aucune donnée personnelle (téléphone, identifiant) en entrée du modèle ni dans les journaux de prédiction ; référence client opaque `customer_ref`.
- Durée de conservation des journaux de prédiction : 13 mois, puis agrégation.
- Accès : remote DVC et registre MLflow en lecture pour les Data Scientists, écriture réservée au pipeline CI/CT et aux ML Engineers.

## Auditabilité des décisions
Pour toute prédiction on peut retrouver : `request_id` → version du modèle (réponse API + journal) → `run_id` MLflow → commit Git + hash DVC des données d'entraînement → paramètres et métriques. Les promotions et rollbacks sont tracés (qui, quand, pourquoi) dans `reports/registry_audit.jsonl` et dans les tags du registre. Les probabilités renvoyées par l'API et l'importance des variables permettent d'expliquer une décision à un client ou au régulateur.
