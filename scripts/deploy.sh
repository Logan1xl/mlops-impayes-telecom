#!/usr/bin/env bash
# Déploiement Kubernetes (stable + canary via NGINX Ingress canary-weight).
#   ./scripts/deploy.sh staging  <image>
#   ./scripts/deploy.sh canary   <image> <poids%>
#   ./scripts/deploy.sh full     <image>
#   ./scripts/deploy.sh rollback
#   ./scripts/deploy.sh local                 # docker compose (démo en local)
set -euo pipefail
MODE=${1:?mode}; IMAGE=${2:-}; WEIGHT=${3:-10}
NS=impayes

case "$MODE" in
  local)
    docker compose up -d --build ;;
  staging)
    kubectl -n "$NS-staging" set image deployment/impayes-api api="$IMAGE"
    kubectl -n "$NS-staging" rollout status deployment/impayes-api --timeout=180s ;;
  canary)
    kubectl -n "$NS" set image deployment/impayes-api-canary api="$IMAGE"
    kubectl -n "$NS" rollout status deployment/impayes-api-canary --timeout=180s
    kubectl -n "$NS" annotate ingress impayes-api-canary \
      nginx.ingress.kubernetes.io/canary-weight="$WEIGHT" --overwrite
    echo "Canary actif sur ${WEIGHT}% du trafic" ;;
  full)
    kubectl -n "$NS" set image deployment/impayes-api api="$IMAGE"
    kubectl -n "$NS" rollout status deployment/impayes-api --timeout=300s
    kubectl -n "$NS" annotate ingress impayes-api-canary nginx.ingress.kubernetes.io/canary-weight="0" --overwrite ;;
  rollback)
    kubectl -n "$NS" annotate ingress impayes-api-canary nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
    kubectl -n "$NS" rollout undo deployment/impayes-api-canary || true
    echo "Rollback effectué : 100 % du trafic sur la version stable" ;;
  *) echo "mode inconnu: $MODE" >&2; exit 2 ;;
esac
