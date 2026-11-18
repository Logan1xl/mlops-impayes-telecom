#!/bin/bash
# NaijaTel Impayés AI — lanceur de démonstration (Linux)
cd "$(dirname "$0")" || exit 1
(xdg-open index.html 2>/dev/null || sensible-browser index.html 2>/dev/null || echo "Ouvrez $(pwd)/index.html dans un navigateur") &
echo "NaijaTel Impayés AI — démo lancée (100 % hors-ligne)."
echo "MLflow live : cd .. && .venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000"
