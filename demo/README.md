# NaijaTel Impayés AI — le produit

Démo **100 % hors-ligne** pour la soutenance du CC1 : une page web autonome, sans aucune installation (ni Python, ni Docker, ni connexion).

## Comment la présenter (3 scénarios de salle)

| Salle | Quoi faire | Résultat |
|---|---|---|
| Aucune machine avec logiciel | Copier le dossier `demo/` sur une clé USB, double-cliquer `index.html` (ou `Lancer_Demo_macOS.command` / `.bat` / `.sh`) | La démo s'ouvre dans le navigateur par défaut |
| Machine du présentateur avec le projet | `./Lancer_Demo_macOS.command` puis, dans un second terminal : `mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000` et/ou `uvicorn impayes.api.main:app --port 8000` | Onglet « Traçabilité » + MLflow live côte à côte ; la démo bascule auto en « Mode connecté » |
| Démo très courte (5 min) | Onglet « Démo produit » uniquement : 1 profil fidèle → verdict vert ; 1 profil « Client à gros risque » → verdict rouge ; montrer l'export CSV du registre | Le jury voit l'IA + la traçabilité d'une décision |

## Plan de présentation suggéré (≈ 12 min)

1. **Démo produit** (3 min) — saisir un profil en direct, montrer les probabilités, les facteurs dominants, le registre local et l'export CSV. Souligner : zéro donnée sortie de la machine.
2. **Argumentaire** (3 min) — problème (impayés), démonstrateur ROI en direct (bouger les curseurs !), offres Starter / Pro / Entreprise.
3. **Performance** (3 min) — vrais chiffres du jeu HF : F1-macro 0,469, rappel « high » 0,674, quality gate ✅, matrice de confusion, honnêteté méthodologique (la réplique synthétique donnait 0,649).
4. **Traçabilité MLflow** (3 min) — runs réels (LogReg retenu, run `2805ad80`), tags `git_commit` + `data_version` DVC, journal d'audit (`DONGMO WOZE Junior` a promu v1 → production), chaîne `request_id → … → dvc.lock`. Puis ouvrir MLflow UI pour la preuve vivante.

## Régénérer les artefacts (après un `dvc repro`)

```bash
python scripts/export_demo_assets.py
```

Cela réécrit `demo/assets/model.json|metrics.json|trace.json` **et** leurs variantes JS (`model.js`, `metrics.js`, `trace.js`) — l'inférence JS reste bit-compatible avec scikit-learn (vérifiée à 4·10⁻⁷ près).

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
└── README.md                # ce fichier
```
