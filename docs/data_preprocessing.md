# Prétraitement et feature engineering

## 1. Source et versionnement

| Élément | Valeur |
|---|---|
| Jeu | *Telecom Credit Scoring Data (Nigeria)* — Electric Sheep Africa (Hugging Face) |
| Fichier | `telecom_credit_scoring_data.parquet` (500 000 lignes, 15 colonnes) |
| Récupération | `python -m impayes.data.download` → `data/raw/` + `data/raw/SOURCE.json` (origine, date, nb de lignes) |
| Versionnement | `dvc add data/raw/telecom_credit_scoring_data.parquet` → hash MD5 dans le `.dvc`, fichier poussé sur le remote DVC |
| Lien modèle ↔ données | le hash DVC est écrit dans chaque run MLflow (`data_version`) et sur la version du registre |

Hors connexion, `--allow-synthetic` génère une **réplique synthétique** de même schéma (`impayes/data/synthetic.py`), signalée comme telle dans `SOURCE.json`. Elle ne sert qu'à tester la chaîne.

## 2. Contrat de données (étape `validate`)

Règles **bloquantes** : présence des 15 colonnes, types, absence de valeurs manquantes sur les variables utilisées, plages (`tenure_months` 1–120, `payment_consistency_score` 0–1, `recharge_frequency_per_month` 0–31…), domaines (`operator` ∈ {MTN, Airtel, Glo, 9mobile}, `account_type` ∈ {prepaid, postpaid}, `default_risk` ∈ {low, medium, high}), volume minimal.
Règles **d'avertissement** : unicité de `customer_id`, part de la classe minoritaire ≥ 5 %.
Résultat : `reports/data_validation.json`. Un échec bloquant arrête le pipeline (code 1).

## 3. Sélection des variables

| Colonne | Décision | Raison |
|---|---|---|
| `tenure_months`, `avg_monthly_spend_ngn`, `recharge_frequency_per_month`, `payment_consistency_score`, `late_payment_count` | **gardées** | comportement d'usage et de paiement (cité dans l'énoncé) |
| `operator`, `account_type` | **gardées** | contexte client (one-hot) |
| `customer_id`, `phone_number` | exclues | identifiants / données personnelles (NDPR, RGPD) |
| `assessment_date` | exclue | constante (30/09/2025) |
| `credit_score`, `credit_rating`, `loan_eligibility`, `max_loan_amount_ngn` | exclues | sorties d'un autre système de scoring calculées en même temps que la cible : **fuite d'information** et dépendance circulaire. `credit_rating` est une simple discrétisation de `credit_score` (poor < 500 ≤ fair < 650 ≤ good < 800 ≤ excellent) |

## 4. Variables dérivées (`TelecomFeatures`)

| Variable | Formule | Intuition |
|---|---|---|
| `spend_per_recharge` | dépense / max(recharges, 1) | montant moyen par recharge |
| `late_rate` | retards / max(ancienneté, 1) | retards rapportés à la durée de relation |
| `log_spend` | log(1 + dépense) | réduit l'asymétrie |
| `is_new_customer` | ancienneté < 6 mois | clients récents plus incertains |

Le transformateur fait partie du **pipeline scikit-learn sérialisé** : l'API applique exactement la même transformation qu'à l'entraînement (pas de *training/serving skew*).

## 5. Encodage, normalisation, découpage

- Numériques : `StandardScaler` ; catégorielles : `OneHotEncoder(handle_unknown="ignore")` (une catégorie inconnue en production ne fait pas planter l'API).
- Découpage **stratifié** 70 % train / 10 % validation / 20 % test, graine `42`.
- Le **jeu de référence** pour la dérive (50 000 lignes du train) est écrit dans `data/reference/`.
- Déséquilibre des classes : `class_weight="balanced"` ; métrique principale **F1-macro**, métrique métier **rappel de la classe `high`**.
