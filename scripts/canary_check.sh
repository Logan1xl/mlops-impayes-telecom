#!/usr/bin/env bash
# Observe le canary puis applique les critères de rollback (sort en erreur => job rollback).
#   ./scripts/canary_check.sh <prometheus_url> <durée_s>
set -euo pipefail
PROM=${1:?prometheus}; WAIT=${2:-1800}
sleep "$WAIT"
q() { curl -fsS --get "$PROM/api/v1/query" --data-urlencode "query=$1" | jq -r '.data.result[0].value[1] // "0"'; }
ERR=$(q 'sum(rate(impayes_requests_total{track="canary",status=~"5.."}[30m])) / clamp_min(sum(rate(impayes_requests_total{track="canary"}[30m])),1e-9)')
P95=$(q 'histogram_quantile(0.95, sum(rate(impayes_inference_latency_seconds_bucket{track="canary"}[30m])) by (le))')
HIGH_C=$(q 'sum(rate(impayes_predictions_total{track="canary",default_risk="high"}[30m])) / clamp_min(sum(rate(impayes_predictions_total{track="canary"}[30m])),1e-9)')
HIGH_S=$(q 'sum(rate(impayes_predictions_total{track="stable",default_risk="high"}[30m])) / clamp_min(sum(rate(impayes_predictions_total{track="stable"}[30m])),1e-9)')
echo "canary: erreurs=$ERR p95=${P95}s part_high=$HIGH_C (stable: $HIGH_S)"
fail=0
awk "BEGIN{exit !($ERR > 0.01)}"  && { echo "ROLLBACK : taux d'erreur > 1 %"; fail=1; }
awk "BEGIN{exit !($P95 > 0.30)}"  && { echo "ROLLBACK : latence p95 > 300 ms"; fail=1; }
awk "BEGIN{d=$HIGH_C-$HIGH_S; if(d<0)d=-d; exit !(d > 0.10)}" && { echo "ROLLBACK : écart de part « high » > 10 pts"; fail=1; }
exit $fail
