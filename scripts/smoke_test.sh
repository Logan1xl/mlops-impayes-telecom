#!/usr/bin/env bash
# Tests de fumée après déploiement : santé, contrat de /predict, rejet d'entrée invalide.
set -euo pipefail
URL=${1:-http://localhost:8000}
curl -fsS "$URL/health" | grep -q '"ok"'
OK='{"tenure_months":47,"avg_monthly_spend_ngn":38033.69,"recharge_frequency_per_month":19,"payment_consistency_score":0.61,"late_payment_count":1,"operator":"MTN","account_type":"prepaid"}'
curl -fsS -X POST "$URL/predict" -H 'content-type: application/json' -d "$OK" | grep -Eq '"default_risk":"(low|medium|high)"'
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$URL/predict" -H 'content-type: application/json' -d '{"tenure_months":-3}')
[ "$code" = "422" ]
echo "Smoke tests OK sur $URL"
