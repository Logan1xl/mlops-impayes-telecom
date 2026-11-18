# NaijaTel Impayés AI — le produit

Démo **100 % hors-ligne** pour la soutenance du CC1 : une page web autonome, sans aucune installation (ni Python, ni Docker, ni connexion).

## Comment la présenter (3 scénarios de salle)

| Salle | Quoi faire | Résultat |
|---|---|---|
| Aucune machine avec logiciel | Copier le dossier `demo/` sur une clé USB, double-cliquer `index.html` (ou `Lancer_Demo_macOS.command` / `.bat` / `.sh`) | La démo s'ouvre dans le navigateur par défaut |
| Machine avec **seulement le binaire** (sans Python) | Double-cliquer `dist/NaijaTel-ImpayesAI-Demo.app` (7,6 Mo, macOS arm64) — construit avec PyInstaller | Le navigateur s'ouvre tout seul sur la démo servie en local |
| Machine du présentateur avec le projet | `./Lancer_Demo_macOS.command` puis, dans un second terminal : `mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000` et/ou `uvicorn impayes.api.main:app --port 8000` | Onglet « Traçabilité » + MLflow live côte à côte ; la démo bascule auto en « Mode connecté » |
| Démo très courte (5 min) | Onglet « Démo produit » uniquement : 1 profil fidèle → verdict vert ; 1 profil « Client à gros risque » → verdict rouge ; montrer l'export CSV du registre | Le jury voit l'IA + la traçabilité d'une décision |

> **Exécutable autonome** (`dist/NaijaTel-ImpayesAI-Demo`) — embarque la démo entière ; la machine cible n'a besoin de **rien** (ni Python, ni Docker, ni réseau). macOS Gatekeeper : clic droit → Ouvrir la première fois. Binaire **ARM64 macOS** : sur Windows, compiler sur Windows (`pip install pyinstaller` puis la commande du `pyi` dans `scripts/standalone_launcher.py`) — ou livrer `Lancer_Demo_Windows.bat` + le dossier `demo/` (moins consensuel, mais zéro build).

## Plan de présentation suggéré (≈ 12 min)

1. **Démo produit** (3 min) — saisir un profil en direct, montrer les probabilités, les facteurs dominants, le registre local et l'export CSV. Souligner : zéro donnée sortie de la machine.
2. **Argumentaire** (3 min) — problème (impayés), démonstrateur ROI en direct (bouger les curseurs !), offres Starter / Pro / Entreprise.
3. **Performance** (3 min) — vrais chiffres du jeu HF : F1-macro 0,469, rappel « high » 0,674, quality gate ✅, matrice de confusion, honnêteté méthodologique (la réplique synthétique donnait 0,649).
4. **Traçabilité MLflow** (3 min) — runs réels (LogReg retenu, run `2805ad80`), tags `git_commit` + `data_version` DVC, journal d'audit (`DONGMO WOZE Junior` a promu v1 → production), chaîne `request_id → … → dvc.lock`. Puis ouvrir MLflow UI pour la preuve vivante.

## Si vous ré-entraînez le modèle (la démo change, c'est automatique)

```bash
dvc repro                 # ré-entraîne
make demo-export          # ou : python scripts/export_demo_assets.py
```

`export_demo_assets.py` régénère `demo/assets/model.js` (mêmes coefficients que `models/model.joblib`), `metrics.js`, `trace.js`. **Le meilleur modèle courant est LogReg** : la démo tourne alors 100 % hors-ligne. Si un ré-entraînement retient un autre algorithme (HistGBM…), le script écrit un marqueur « unsupported » et l'app bascule automatiquement en **mode connecté** (API requise) — jamais de coefficients approximés en douce. L'inférence JS reste bit-compatible avec scikit-learn (vérifiée à 4·10⁻⁷ près).

## MLflow : deux façons de le montrer

1. **Live (recommandée en salle)** — `mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000` → mêmes runs/artefacts/registre (déjà vérifiée).
2. **Dans Docker (notre image dédiée)** — l'image `docker/Dockerfile.mlflow` (mlflow 3.18.0 épinglé, non-root, healthcheck) est construite et testée : `docker compose up -d mlflow` puis http://localhost:5000. Note : cette instance démarre **neuve** (volume `mlflow-data` vide) — le clone du livrable montrera runs + registre via `mlflow ui` côté hôte, pas via l'instance compose.

## Structure

```
demo/
├── index.html               # le produit (1 seul fichier HTML + assets)
├── assets/
│   ├── app.css              # design system (aucun framework)
│   ├── app.js               # onglets, inférence JS, registre, ROI…
│   ├── model.js/.json       # scaler + OHE + coefficients LogReg (2 Ko)
│   ├── metrics.js/.json     # métriques test réelles
│   └── trace.js/.json       # export MLflow (runs, audit, registre)
├── Lancer_Demo_macOS.command / Lancer_Demo_Windows.bat / Lancer_Demo_Linux.sh
├── dist/NaijaTel-ImpayesAI-Demo(.app)   # exécutable autonome (PyInstaller, 7,6 Mo)
└── README.md                # ce fichier
```
