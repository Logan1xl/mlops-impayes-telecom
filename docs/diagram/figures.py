"""Figures du rapport (même charte que l'architecture).

    python docs/diagram/figures.py
Sorties : docs/figures/*.png (+ .drawio pour le pipeline CI/CD/CT)
"""
from figkit import BLUE, GREEN, GREY, HERE, INK, ORANGE, Arrow, Figure, Icon, Rect, Text, card, note

OUT = HERE.parent / "figures"
OUT.mkdir(exist_ok=True)
RED = "#C00000"


def row_cards(fig, y, h, items, x0=40, gap=24, icon_d=44, arrows=False, **kw):
    n = len(items)
    w = (fig.w - 2 * x0 - gap * (n - 1)) / n
    for i, it in enumerate(items):
        ic, t, d = it[:3]
        extra = it[3] if len(it) > 3 else {}
        card(fig, x0 + i * (w + gap), y, w, h, t, d, icon=ic, icon_d=icon_d, **(kw | extra))
        if arrows and i:
            ay = y + 16 + icon_d / 2
            fig.add(Arrow([(x0 + i * (w + gap) - gap + 2, ay), (x0 + i * (w + gap) - 3, ay)]))
    return w


# 1. Les quatre difficultés (R5) ---------------------------------------------
f = Figure(1200, 270, "Quatre difficultés d'un modèle resté sur le poste du développeur")
row_cards(f, 62, 160, [
    ("FaLaptop", "Non industrialisé", ["tourne sur une seule machine :", "ni disponible, ni scalable"], {"accent": RED}),
    ("FaHandPaper", "Mises à jour manuelles", ["erreurs, lenteur, aucune", "version à laquelle revenir"], {"accent": RED}),
    ("FaEyeSlash", "Aucune surveillance", ["la dérive des données", "passe inaperçue"], {"accent": RED}),
    ("FaBalanceScale", "Aucune traçabilité", ["impossible d'expliquer", "une décision de crédit"], {"accent": RED}),
], desc_size=13.5, title_size=16)
note(f, 236, ["Un F1-score de 0,88 mesuré une seule fois hors ligne ne dit rien de la performance réelle du modèle six mois plus tard."])
f.png(OUT / "f01_difficultes.png")

# 2. CI, CD, CT (R3) ----------------------------------------------------------
f = Figure(1200, 290, "Trois boucles d'automatisation complémentaires")
row_cards(f, 62, 178, [
    ("FaVial", "CI — Intégration continue", ["à chaque modification du code :", "tests, contrôle des données,", "entraînement de contrôle"]),
    ("FaRocket", "CD — Déploiement continu", ["le modèle validé est empaqueté", "puis mis en service par étapes,", "avec retour arrière possible"]),
    ("FaSyncAlt", "CT — Entraînement continu", ["spécifique au ML : le modèle", "est réentraîné sur des données", "récentes quand c'est justifié"], {"accent": ORANGE}),
], arrows=True, desc_size=13.5, title_size=16)
note(f, 256, ["La CI vérifie, le CD livre, le CT maintient le modèle à jour : seul le CT n'a pas d'équivalent en DevOps classique."])
f.png(OUT / "f02_ci_cd_ct.png")

# 3. La chaîne MLOps en 7 étapes (R6) -----------------------------------------
f = Figure(1400, 300, "La chaîne MLOps du projet, de la donnée à la surveillance")
w = row_cards(f, 62, 185, [
    ("FaDatabase", "1. Ingestion", ["collecte et", "contrôle qualité"]),
    ("FaCodeBranch", "2. Préparation", ["variables,", "versions DVC"]),
    ("FaFlask", "3. Entraînement", ["essais suivis", "dans MLflow"]),
    ("FaClipboardCheck", "4. Validation", ["seuils, registre", "de modèles"]),
    ("FaBoxOpen", "5. Déploiement", ["API dans une", "image Docker"]),
    ("FaChartLine", "6. Surveillance", ["dérive, latence,", "alertes"]),
    ("FaSyncAlt", "7. Réentraînement", ["si la dérive", "est confirmée"], {"accent": ORANGE}),
], gap=18, arrows=True, desc_size=13, title_size=14.5, icon_d=42)
f.add(Arrow([(1400 - 40 - w / 2, 248), (1400 - 40 - w / 2, 268), (40 + 2 * (w + 18) + w / 2, 268),
             (40 + 2 * (w + 18) + w / 2, 250)], color=ORANGE, dash=True))
note(f, 274, ["retour vers l'entraînement"], size=11.5, color=ORANGE)
f.h = 300
f.png(OUT / "f03_chaine_mlops.png")

# 4. Data drift vs concept drift (Q7) ----------------------------------------
f = Figure(1200, 360, "Data drift et concept drift : deux dérives différentes")
for k, (ic, t, sub, lines, col) in enumerate([
    ("FaWaveSquare", "Data drift", "les entrées changent : P(X)",
     ["Exemple : l'inflation du naira augmente", "les dépenses mensuelles de 60 %, sans que", "les clients paient moins bien.",
      "Détection sans attendre les labels :", "PSI, test de Kolmogorov-Smirnov, χ²."], BLUE),
    ("FaRandom", "Concept drift", "la relation change : P(Y | X)",
     ["Exemple : après une crise, à profil égal,", "un client avec 3 retards fait plus souvent", "défaut qu'avant.",
      "Détection avec les impayés réellement", "constatés : baisse du F1, du rappel."], ORANGE)]):
    x = 40 + k * 570
    f.add(Rect(x, 62, 550, 260, fill="#FFFFFF", stroke=col, shadow=True))
    f.add(Icon(ic, x + 48, 110, d=50, bg=col))
    f.add(Text(x + 86, 88, 440, [t], size=18, bold=True, color=col, align="start"))
    f.add(Text(x + 86, 114, 440, [sub], size=13.5, italic=True, color=GREY, align="start"))
    f.add(Text(x + 30, 160, 500, lines[:3], size=14, color=INK, align="start"))
    f.add(Text(x + 30, 240, 500, lines[3:], size=14, color=GREY, align="start", italic=True))
f.png(OUT / "f04_drifts.png")

# 5. Redéploiement progressif (Q8) -------------------------------------------
f = Figure(1200, 300, "Un redéploiement progressif et réversible")
stages = [("FaVial", "Staging", ["tests de fumée"]), ("FaUserCheck", "Validation", ["approbation", "humaine"]),
          ("FaFilter", "Canary 10 %", ["30 minutes", "d'observation"], {"accent": ORANGE}),
          ("FaChartLine", "25 % puis 50 %", ["si tout reste", "dans les seuils"]),
          ("FaRocket", "100 %", ["alias production,", "audit"], {"accent": GREEN})]
row_cards(f, 62, 165, stages, gap=26, arrows=True, desc_size=13, title_size=15, icon_d=42)
f.add(Rect(330, 245, 540, 32, fill="#FFFFFF", stroke=RED, r=16))
f.add(Icon("FaUndo", 350, 261, d=24, bg=RED))
f.add(Text(370, 252, 490, ["Un critère au rouge  →  retour immédiat à la version précédente"], size=13.5, bold=True, color=RED,
           align="start"))
f.png(OUT / "f05_canary.png")

# 6. Cycle de vie d'une version de modèle (iv) -------------------------------
f = Figure(1200, 260, "Cycle de vie d'une version dans le registre MLflow")
row_cards(f, 62, 150, [
    ("FaFlask", "candidate", ["vient d'être", "entraînée"]),
    ("FaClipboardCheck", "staging", ["seuils de qualité", "franchis"]),
    ("FaRocket", "production", ["approuvée et", "canary réussi"], {"accent": GREEN}),
    ("FaArchive", "previous_production", ["conservée pour", "le retour arrière"], {"accent": "#7F7F7F"}),
], gap=36, arrows=True, desc_size=13.5, title_size=16, icon_d=42)
note(f, 228, ["Seule la promotion en production exige une approbation humaine ; chaque changement est inscrit au journal d'audit."])
f.png(OUT / "f06_cycle_vie.png")

# 7. Trois niveaux de surveillance (iii) ------------------------------------
f = Figure(1200, 300, "Trois niveaux de surveillance, trois questions")
row_cards(f, 62, 190, [
    ("FaTachometerAlt", "Opérationnel", ["Le service répond-il ?", "latence p95 > 300 ms", "erreurs 5xx > 1 %"]),
    ("FaDatabase", "Données", ["Les entrées ressemblent-elles", "à l'entraînement ?", "PSI ≥ 0,10 alerte · ≥ 0,25 critique"]),
    ("FaBullseye" if False else "FaSearch", "Modèle", ["Les prédictions sont-elles justes ?", "baisse du F1 ≥ 0,05 alerte",
                                                     "≥ 0,10 critique"], {"accent": ORANGE}),
], desc_size=13.5, title_size=16)
note(f, 266, ["Les deux premiers niveaux se mesurent en continu ; le troisième attend les impayés constatés (30 à 60 jours)."])
f.png(OUT / "f07_niveaux_monitoring.png")

# 8. Pipeline CI / CD / CT (ii) — avec version draw.io -----------------------
f = Figure(1500, 720, "Pipeline CI / CD / CT : étapes automatiques et points de contrôle")
lanes = [
    ("CI — à chaque push ou pull request", BLUE, [
        ("FaCodeBranch", "Push / PR", ["déclencheur"]), ("FaSearch", "Lint", ["ruff"]), ("FaVial", "32 tests", ["pytest"]),
        ("FaFlask", "Pipeline", ["dvc repro"]), ("FaClipboardCheck", "Quality gate", ["seuils F1, rappel"]),
        ("FaCube", "Image", ["build + scan"])], "échec : fusion bloquée", 4),
    ("CD — après fusion sur la branche principale", GREEN, [
        ("FaTags", "Version", ["alias staging"]), ("FaCube", "Publication", ["registre d'images"]),
        ("FaVial", "Staging", ["tests de fumée"]), ("FaUserCheck", "Approbation", ["Direction du risque"]),
        ("FaFilter", "Canary 10 %", ["30 min"]), ("FaRocket", "Production", ["100 % du trafic"])], "critère KO : rollback", 4),
    ("CT — chaque nuit à 03:00 ou sur alerte", ORANGE, [
        ("FaCalendarAlt", "Planification", ["cron / alerte"]), ("FaWaveSquare", "Surveillance", ["PSI, KS, F1 réel"]),
        ("FaFilter", "Décision", ["dérive confirmée ?"]), ("FaDatabase", "Données", ["fenêtre récente"]),
        ("FaFlask", "Réentraînement", ["dvc repro"]), ("FaUserCheck", "PR de promotion", ["revue humaine"])],
     "gate KO : modèle actuel conservé", 4),
]
for k, (title, col, steps, fail, fi) in enumerate(lanes):
    y = 58 + k * 212
    f.add(Rect(30, y, 1440, 198, fill="#FFFFFF", stroke=col, r=8))
    f.add(Text(50, y + 12, 900, [title], size=15.5, bold=True, color=col, align="start"))
    for i, (ic, t, d) in enumerate(steps):
        cx = 150 + i * 240
        f.add(Icon(ic, cx, y + 72, d=44, bg=col))
        f.add(Text(cx - 100, y + 100, 200, [t], size=14, bold=True, color=INK))
        f.add(Text(cx - 100, y + 120, 200, d, size=12.5, color=GREY))
        if i:
            f.add(Arrow([(cx - 240 + 30, y + 72), (cx - 30, y + 72)], color=col))
    fx = 150 + fi * 240
    f.add(Arrow([(fx, y + 140), (fx, y + 154)], color=RED, sw=1.3, dash=True))
    pw = len(fail) * 6.4 + 30
    f.add(Rect(fx - pw / 2, y + 156, pw, 28, fill="#FFFFFF", stroke=RED, r=14, sw=1.2))
    f.add(Text(fx - pw / 2, y + 162, pw, [fail], size=12.5, bold=True, color=RED))
note(f, 694, ["Le CT ne met jamais un modèle en production : il ouvre une demande de fusion, dont l'acceptation déclenche le CD."],
     size=12.5)
f.save(HERE.parent / "pipeline_ci_cd_ct", "Pipeline CI CD CT")
f.png(OUT / "f08_pipeline.png")
print("figures ok")
