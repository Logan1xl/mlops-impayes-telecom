# Model card — `impayes-default-risk`

> Les chiffres ci-dessous sont régénérés par `make pipeline` dans `reports/metrics.json`.
> Valeurs indicatives **obtenues sur la réplique synthétique** de même schéma. Relancer le pipeline sur le vrai jeu et reporter les nouvelles valeurs ici.

## Usage prévu
Classer chaque abonné en risque d'impayé `low` / `medium` / `high` pour **aider** les équipes risque et recouvrement (plafond de crédit airtime, relances préventives). Le modèle **n'est pas** un outil de décision automatique de refus de service : toute décision défavorable doit pouvoir être revue par un humain.

## Données
*Telecom Credit Scoring Data (Nigeria)*, 500 000 clients, 15 colonnes. Variables utilisées et exclusions : voir `docs/data_preprocessing.md`.

## Modèles comparés (validation)
| Candidat | F1-macro | Rappel `high` | AUC OvR | Temps d'entraînement |
|---|---|---|---|---|
| Régression logistique | 0,649 | 0,682 | 0,837 | 1 s |
| Random Forest | 0,649 | 0,659 | 0,834 | 18 s |
| **HistGradientBoosting (retenu)** | **0,649** | 0,660 | 0,835 | 4 s |

## Performance sur le jeu de test (40 000 lignes)
| Métrique | Valeur |
|---|---|
| Accuracy | 0,664 |
| Précision macro | 0,663 |
| Rappel macro | 0,650 |
| **F1-macro** | **0,646** |
| Rappel / précision `high` | 0,665 / 0,768 |
| AUC one-vs-rest macro | 0,832 |
| Latence p50 / p95 (1 ligne) | 8 ms / 12 ms |

La classe `medium` est la plus difficile (F1 0,47) : elle se situe entre deux comportements et concentre les confusions.

## Limites et risques
- Données **synthétiques** (le jeu Hugging Face est lui-même généré) : les relations apprises peuvent différer de la réalité d'un opérateur.
- Sensible à l'inflation (dépenses en NGN) → surveillance PSI de `avg_monthly_spend_ngn`.
- Équité : `operator` a une importance quasi nulle ; test automatique `test_operator_change_has_limited_effect`.

## Traçabilité
Chaque version du registre porte : `run_id` MLflow, `git_commit`, `data_version` (hash DVC), `test_f1_macro`, `quality_gate`, approbateur (`approved_production_by`). Journal des promotions : `reports/registry_audit.jsonl`.
