"""Figure principale : architecture MLOps cible (lecture de gauche à droite).

    python docs/diagram/architecture.py
Sorties : docs/architecture.{png,svg,drawio}
"""
from figkit import BLUE, FILL, GREEN, GREY, HERE, INK, LINE, ORANGE, Arrow, Figure, Icon, Rect, Text, card, note

W, H = 1600, 815
fig = Figure(W, H, "Architecture MLOps cible : du jeu de données au modèle surveillé en production")

# --- bandeau CI/CD au-dessus des étapes 2 à 5 --------------------------------
X = [40, 300, 560, 820, 1080, 1340]          # abscisses des 6 cartes
CW, CY, CH = 220, 160, 222
fig.add(Rect(X[1] - 10, 62, X[4] + CW - X[1] + 20, 72, fill="#FFFFFF", stroke=BLUE, dash=True, r=8))
fig.add(Icon("FaCogs", X[1] + 34, 98, d=40))
fig.add(Text(X[1] + 64, 74, 600, ["Automatisation CI / CD — GitHub Actions"], size=15, bold=True, color=BLUE, align="start"))
fig.add(Text(X[1] + 64, 96, 900, ["À chaque modification : tests  →  entraînement de contrôle  →  construction de l'image  "
                                   "→  déploiement progressif"], size=12.5, color=GREY, align="start"))

# --- 6 étapes principales -----------------------------------------------------
steps = [
    ("FaDatabase", "Données", ["Historique des abonnés :", "factures, recharges, retards", "(500 000 clients)"], "Hugging Face · SI"),
    ("FaCodeBranch", "Préparation", ["Contrôle qualité, variables", "dérivées, découpage", "train / validation / test"], "DVC"),
    ("FaFlask", "Entraînement", ["3 modèles comparés,", "paramètres et scores", "enregistrés à chaque essai"], "scikit-learn · MLflow"),
    ("FaClipboardCheck", "Validation", ["Seuils de qualité vérifiés,", "version enregistrée", "dans le registre"], "MLflow Registry"),
    ("FaBoxOpen", "Déploiement", ["Image Docker immuable,", "API de prédiction,", "mise en service progressive"], "Docker · FastAPI"),
    ("FaUsers", "Utilisation", ["Applications métier :", "octroi de crédit,", "relances préventives"], "POST /predict"),
]
for i, (ic, t, d, tag) in enumerate(steps):
    card(fig, X[i], CY, CW, CH, t, d, icon=ic, tag=tag, num=str(i + 1), title_size=16.5, desc_size=13.5)
for i in range(5):
    y = CY + 92
    fig.add(Arrow([(X[i] + CW + 2, y), (X[i + 1] - 4, y)]))

# --- référentiels (sous les étapes 1 à 3) ------------------------------------
RY, RH = 440, 175
fig.add(Rect(X[0], RY, X[2] + CW - X[0], RH, fill="#FFFFFF", stroke=LINE, r=8))
fig.add(Text(X[0] + 18, RY + 14, 500, ["Référentiels versionnés : tout est traçable"], size=15, bold=True, color=BLUE,
             align="start"))
refs = [("FaGitAlt", "Git", ["code et paramètres"]), ("FaHdd", "Stockage DVC", ["versions des données"]),
        ("FaHistory", "MLflow", ["essais et modèles"])]
for j, (ic, t, d) in enumerate(refs):
    cx = X[0] + 130 + j * 245
    fig.add(Icon(ic, cx, RY + 82, d=46, bg="#5B7FA6"))
    fig.add(Text(cx - 110, RY + 112, 220, [t], size=14, bold=True, color=INK))
    fig.add(Text(cx - 110, RY + 132, 220, d, size=12.5, color=GREY))
for i in range(3):                                         # liens pointillés vers chaque étape
    fig.add(Arrow([(X[i] + CW / 2, CY + CH + 2), (X[i] + CW / 2, RY - 2)], color=LINE, sw=1.4, dash=True, both=True))

# --- surveillance (sous les étapes 4 à 6) ------------------------------------
MX = X[3]
MW = X[5] + CW - X[3]
fig.add(Rect(MX, RY, MW, RH, fill="#FFFFFF", stroke=BLUE, r=8, shadow=True))
fig.add(Text(MX + 18, RY + 14, 500, ["7  Surveillance en production"], size=15, bold=True, color=BLUE, align="start"))
mons = [("FaTachometerAlt", "Santé du service", ["latence, erreurs", "Prometheus · Grafana"]),
        ("FaWaveSquare", "Dérive des données", ["PSI, KS, performance", "sur les impayés réels"]),
        ("FaBell", "Alertes", ["seuils dépassés", "notification équipe"])]
for j, (ic, t, d) in enumerate(mons):
    cx = MX + 125 + j * 245
    fig.add(Icon(ic, cx, RY + 82, d=46))
    fig.add(Text(cx - 115, RY + 112, 230, [t], size=14, bold=True, color=INK))
    fig.add(Text(cx - 115, RY + 132, 230, d, size=12.5, color=GREY))
# flux vers la surveillance
fig.add(Arrow([(X[4] + CW / 2, CY + CH + 2), (X[4] + CW / 2, RY - 2)], label="journal des prédictions",
              label_at=(X[4] + CW / 2, (CY + CH + RY) / 2), label_w=150))
fig.add(Arrow([(X[5] + CW / 2, CY + CH + 2), (X[5] + CW / 2, RY - 2)], label="impayés constatés",
              label_at=(X[5] + CW / 2, (CY + CH + RY) / 2), label_w=120))

# --- boucle de réentraînement -------------------------------------------------
LY = RY + RH + 40
fig.add(Arrow([(MX + MW / 2, RY + RH + 2), (MX + MW / 2, LY), (X[2] + CW + 20, LY), (X[2] + CW + 20, CY + 150),
               (X[2] + CW + 4, CY + 150)], color=ORANGE, sw=2.2))
fig.add(Rect(X[2] + CW + 70, LY - 18, 520, 36, fill="#FFFFFF", stroke=ORANGE, r=18))
fig.add(Icon("FaSyncAlt", X[2] + CW + 90, LY, d=28, bg=ORANGE))
fig.add(Text(X[2] + CW + 110, LY - 9, 490, ["8  Réentraînement (CT) si dérive confirmée, après validation humaine"],
             size=13.5, bold=True, color=ORANGE, align="start"))

# --- gouvernance --------------------------------------------------------------
GY = 700
fig.add(Rect(X[0], GY, X[5] + CW - X[0], 58, fill=FILL, stroke=FILL, r=8))
fig.add(Icon("FaShieldAlt", X[0] + 34, GY + 29, d=38, bg=GREEN))
fig.add(Text(X[0] + 64, GY + 10, 1400, ["Gouvernance"], size=14.5, bold=True, color=GREEN, align="start"))
fig.add(Text(X[0] + 64, GY + 30, 1450, ["Contrat de données · aucune donnée personnelle dans le modèle ni les journaux · "
                                         "journal d'audit des mises en production · retour arrière immédiat (rollback)"],
             size=12.5, color=GREY, align="start"))
note(fig, H - 26, ["Lecture : les étapes 1 à 6 forment le flux principal ; la surveillance (7) peut relancer "
                   "l'entraînement (8), jamais remplacer le modèle sans contrôle."], size=12)

if __name__ == "__main__":
    fig.save(HERE.parent / "architecture", "Architecture MLOps cible")
    print("ok")
