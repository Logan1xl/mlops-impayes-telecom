#!/bin/bash
# NaijaTel Impayés AI — lanceur de démonstration (macOS)
# Double-cliquez sur ce fichier dans le Finder : la démo s'ouvre dans votre navigateur.
cd "$(dirname "$0")" || exit 1
open index.html
echo "════════════════════════════════════════════════"
echo "  NaijaTel Impayés AI — démo ouverte dans votre"
echo "  navigateur. 100 % hors-ligne, aucune installation."
echo "════════════════════════════════════════════════"
echo ""
echo "Optionnel — tracer les expériences MLflow (si le projet est installé) :"
echo "  cd .. && .venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000"
echo "  puis ouvrir http://localhost:5000"
echo ""
echo "Optionnel — API FastAPI live :"
echo "  cd .. && .venv/bin/uvicorn impayes.api.main:app --port 8000"
echo "  (la démo bascule automatiquement en « Mode connecté »)"
echo ""
read -n 1 -s -r -p "Appuyez sur une touche pour fermer ce terminal…"
