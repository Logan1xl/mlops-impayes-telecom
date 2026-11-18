#!/usr/bin/env python
"""Génère la présentation de la soutenance CC1 (PowerPoint 16:9).

  python scripts/build_presentation.py
  → Presentation_CC1_ImpayesAI.pptx (à côté du dépôt)

Design : navy + teal + ambre, figures du rapport réutilisées (docs/figures/),
métriques réelles du vrai jeu Hugging Face (reports/metrics.json).
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = Path.home() / "Downloads/CC1_MLOps_MBONGO_DONGMO/mlops-impayes-telecom/docs/figures"
ARCH = ROOT / "docs/architecture.png"
PIPELINE = ROOT / "docs/pipeline_ci_cd_ct.png"
OUT = ROOT.parent / "Presentation_CC1_ImpayesAI.pptx"

M = json.loads((ROOT / "reports/metrics.json").read_text())
CMP = json.loads((ROOT / "reports/model_comparison.json").read_text())
TRACE = json.loads((ROOT / "demo/assets/trace.json").read_text())

NAVY_DARK = RGBColor(0x08, 0x1A, 0x33)
NAVY = RGBColor(0x0B, 0x25, 0x45)
NAVY_MID = RGBColor(0x16, 0x4E, 0x7E)
NAVY_SOFT = RGBColor(0x1E, 0x3A, 0x5F)
TEAL = RGBColor(0x0F, 0xB5, 0xA8)
TEAL_DARK = RGBColor(0x0F, 0x76, 0x6E)
TEAL_PALE = RGBColor(0xEA, 0xFA, 0xF7)
AMBER = RGBColor(0xFB, 0xBF, 0x24)
ROSE = RGBColor(0xF4, 0x3F, 0x5E)
ROSE_PALE = RGBColor(0xFF, 0xE9, 0xEC)
GREEN = RGBColor(0x22, 0xC5, 0x5E)
GREEN_PALE = RGBColor(0xE7, 0xF9, 0xEE)
PAPER = RGBColor(0xF4, 0xF7, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x0F, 0x24, 0x40)
MUTED = RGBColor(0x5B, 0x6D, 0x85)
LINE = RGBColor(0xE3, 0xE9, 0xF2)

SERIF = "Georgia"
SANS = "Calibri"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# ---------- helpers ----------

def slide_new():
    return prs.slides.add_slide(BLANK)

def rect(s, x, y, w, h, fill=None, line=None, line_w=1.0, round_=False, radius=0.06):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE, x, y, w, h)
    if round_:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp

def oval(s, x, y, w, h, fill=None, line=None, line_w=1.0):
    shp = s.shapes.add_shape(MSO_SHAPE.OVAL, x, y, w, h)
    if fill is not None:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    else:
        shp.fill.background()
    if line is not None:
        shp.line.color.rgb = line; shp.line.width = Pt(line_w)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp

def txt(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
        space_after=4, line_spacing=1.0, wrap=True):
    """runs: str | list[par] avec par = list[(text, size, color, bold, font)] ou dict."""
    box = s.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    if isinstance(runs, str):
        runs = [[(runs, 18, INK, False, SANS)]]
    for i, par in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        if isinstance(par, dict):
            par = par.get("runs", [])
            p.alignment = par_align = par.get("align", align) if False else align
        for (t, size, color, bold, font) in par:
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.name = font
            r.font.color.rgb = color
    return box

def txt_cell(cell, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE):
    tf = cell.text_frame
    tf.word_wrap = True
    cell.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    for (t, size, color, bold, font) in runs:
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = font
        r.font.color.rgb = color

def kicker(s, text, x=Inches(1.1), y=Inches(0.55), w=Inches(10), color=TEAL_DARK):
    txt(s, x, y, w, Inches(0.45), [[(text.upper(), 12, color, True, SANS)]], space_after=0)

def title(s, text, y=Inches(0.98), size=25, color=INK, x=Inches(1.1), w=Inches(11.1)):
    txt(s, x, y, w, Inches(1.1), [[(text, size, color, True, SERIF)]], space_after=0, line_spacing=1.02)

def footer(s, page_no, total=24):
    line = rect(s, Inches(1.1), Inches(7.06), Inches(11.13), Pt(0.75), fill=LINE)
    txt(s, Inches(1.1), Inches(7.13), Inches(7.2), Inches(0.3),
        [[("CC1 · MLOps — Impayés télécom", 8.5, MUTED, False, SANS)]], space_after=0)
    txt(s, Inches(8.0), Inches(7.13), Inches(4.2), Inches(0.3),
        [[("MBONGO · DONGMO — 18/11/2026   ", 8.5, MUTED, False, SANS),
           (f"{page_no}/{total}", 8.5, TEAL_DARK, True, SANS)]],
        align=PP_ALIGN.RIGHT, space_after=0)

def bg(s, color=PAPER):
    rect(s, 0, 0, prs.slide_width, prs.slide_height, fill=color)

def pic(s, path, y, max_w=Inches(11.13), max_h=Inches(4.9), x=None):
    im = Image.open(path)
    w, h = im.size
    ratio = h / w
    w_in = min(max_w, int(max_h / ratio))
    h_in = int(w_in * ratio)
    if h_in > max_h:
        h_in = max_h
        w_in = int(max_h / ratio)
    x = x if x is not None else int((prs.slide_width - w_in) / 2)
    return s.shapes.add_picture(str(path), x, y, width=w_in, height=h_in)

def kpi_card(s, x, y, w, h, value, label, sub=None, accent=TEAL_DARK):
    rect(s, x, y, w, h, fill=WHITE, line=LINE, round_=True, radius=0.10)
    rect(s, x, y, Inches(0.14), h, fill=accent)
    txt(s, x + Inches(0.32), y + Inches(0.18), w - Inches(0.42), Inches(0.4),
        [[(label.upper(), 8.5, MUTED, True, SANS)]], space_after=0)
    txt(s, x + Inches(0.32), y + Inches(0.55), w - Inches(0.42), Inches(0.9),
        [[(value, 26, accent, True, SANS)]], space_after=0)
    if sub:
        txt(s, x + Inches(0.32), y + Inches(1.28), w - Inches(0.42), Inches(0.35),
            [[(sub, 8, MUTED, False, SANS)]], space_after=0)

def chip(s, x, y, w, text, fill=TEAL_PALE, color=TEAL_DARK):
    rect(s, x, y, w, Inches(0.42), fill=fill, round_=True, radius=0.5)
    txt(s, x, y + Inches(0.055), w, Inches(0.3), [[(text, 9.5, color, True, SANS)]],
        align=PP_ALIGN.CENTER, space_after=0)

# ---------- 1 · Titre ----------
s = slide_new(); bg(s, NAVY_DARK)
rect(s, 0, Inches(6.62), prs.slide_width, Inches(0.045), fill=TEAL)
# marque
oval(s, Inches(1.1), Inches(0.75), Inches(0.62), Inches(0.62), fill=TEAL)
txt(s, Inches(1.1), Inches(0.75), Inches(0.62), Inches(0.62),
    [[("IA", 15, NAVY_DARK, True, SANS)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=0)
txt(s, Inches(1.95), Inches(0.83), Inches(6), Inches(0.5),
    [[("NAIATEL · MLOPS STUDIO", 10, TEAL, True, SANS)]], anchor=MSO_ANCHOR.MIDDLE, space_after=0)
txt(s, Inches(1.1), Inches(2.05), Inches(11.2), Inches(2.5), [
    [("Industrialisation d'un modèle", 40, WHITE, True, SERIF)],
    [("de prédiction des impayés", 40, WHITE, True, SERIF)],
], space_after=0, line_spacing=1.0)
txt(s, Inches(1.1), Inches(4.15), Inches(11.2), Inches(0.8),
    [[("D'un modèle sur le poste du data scientist — ", 17, RGBColor(0xBC, 0xD4, 0xEA), False, SANS),
       ("à un système en production, tracé, testé, surveillé et gouverné.", 17, TEAL, False, SANS)]],
    space_after=0)
txt(s, Inches(1.1), Inches(5.15), Inches(11.2), Inches(1.2), [
    [("CONTRÔLE CONTINU N°1  ·  Machine Learning et Modélisation des Données", 12, WHITE, True, SANS)],
    [("3IL_4 EADL / JA — Normale Semestre I  ·  Semestre 2026–2027", 11, RGBColor(0x8F, 0xB7, 0xD8), False, SANS)],
    [("MBONGO BOLLO Jarle Wulfrid  ·  DONGMO WOZE Junior   —   Encadrant : Dr KUATE Alain François", 11, RGBColor(0x8F, 0xB7, 0xD8), False, SANS)],
], space_after=2)

# ---------- 2 · Sommaire ----------
s = slide_new(); bg(s)
kicker(s, "Sommaire", color=TEAL_DARK)
title(s, "Le déroulé de la présentation")
items = [
    ("01", "Le problème & le contexte"), ("02", "La chaîne MLOps livrée"),
    ("03", "Les données & le contrat"), ("04", "Entraînement & qualité"),
    ("05", "Résultats réels"), ("06", "Registre, API & Docker"),
    ("07", "CI/CD/CT & monitoring"), ("08", "Le produit & la traçabilité"),
]
for i, (n, t) in enumerate(items):
    row, col = divmod(i, 2)
    x = Inches(1.1 + col * 5.7); y = Inches(1.75 + row * 1.12)
    rect(s, x, y, Inches(5.35), Inches(0.92), fill=WHITE, line=LINE, round_=True, radius=0.18)
    txt(s, x + Inches(0.2), y + Inches(0.1), Inches(1.1), Inches(0.75), [[(n, 26, TEAL, True, SERIF)]], space_after=0)
    txt(s, x + Inches(1.35), y + Inches(0.1), Inches(3.8), Inches(0.75), [[(t, 13.5, INK, True, SANS)]],
        anchor=MSO_ANCHOR.MIDDLE, space_after=0, line_spacing=1.05)
rect(s, Inches(1.1), Inches(6.35), Inches(11.13), Pt(0.75), fill=LINE)
txt(s, Inches(1.1), Inches(6.45), Inches(11.1), Inches(0.4),
    [[("Plan : 20 minutes de présentation + 10 minutes d'échanges — la démo produit se fait en direct (onglet dédié).", 10, MUTED, False, SANS)]], space_after=0)
footer(s, 2)

# ---------- 3 · Le problème ----------
s = slide_new(); bg(s)
kicker(s, "01 · Le problème", color=TEAL_DARK)
title(s, "Un bon modèle… enfermé sur le poste du data scientist")
pic(s, FIG_DIR / "f01_difficultes.png", Inches(1.9), max_w=Inches(11.13), max_h=Inches(1.75))
cards = [
    ("Aucun accès applicatif", "Ni l'octroi de crédit, ni le CRM ne peuvent appeler le modèle."),
    ("Mises à jour manuelles", "Ni version, ni reproductibilité : c'est l'oubli garanti."),
    ("Aucune surveillance", "Le F1 hors ligne ne dit rien du comportement en production."),
    ("Aucune traçabilité", "Impossible d'expliquer à un client quel modèle a refusé son crédit."),
]
for i, (t, d) in enumerate(cards):
    x = Inches(1.1 + (i % 2) * 5.7); y = Inches(4.15 + (i // 2) * 1.15)
    rect(s, x, y, Inches(5.35), Inches(1.0), fill=WHITE, line=LINE, round_=True, radius=0.14)
    rect(s, x, y, Inches(0.12), Inches(1.0), fill=ROSE)
    txt(s, x + Inches(0.3), y + Inches(0.1), Inches(5.0), Inches(0.35), [[(t, 12, INK, True, SANS)]], space_after=0)
    txt(s, x + Inches(0.3), y + Inches(0.43), Inches(5.0), Inches(0.5), [[(d, 9.5, MUTED, False, SANS)]], space_after=0, line_spacing=1.0)
footer(s, 3)

# ---------- 4 · Notre réponse ----------
s = slide_new(); bg(s)
kicker(s, "01 · Objectifs", color=TEAL_DARK)
title(s, "Les 6 promesses industrielles du projet")
promises = [
    ("Versionner", "Données DVC + code Git + paramètres tracés"),
    ("Tracer", "MLflow : chaque run, version et promotion sont audités"),
    ("Valider", "Quality gate automatique : seul un modèle conforme avance"),
    ("Conteneuriser", "API FastAPI dans une image Docker immuable"),
    ("Surveiller", "PSI/KS quotidien + F1 réel + latence, avec alertes"),
    ("Gouverner", "Approbation humaine obligatoire avant la production"),
]
for i, (t, d) in enumerate(promises):
    x = Inches(1.1 + (i % 3) * 3.85); y = Inches(1.85 + (i // 3) * 2.15)
    rect(s, x, y, Inches(3.55), Inches(1.9), fill=NAVY, round_=True, radius=0.14)
    txt(s, x + Inches(0.28), y + Inches(0.22), Inches(3.0), Inches(0.35), [[(f"0{i+1}", 11, TEAL, True, SANS)]], space_after=0)
    txt(s, x + Inches(0.28), y + Inches(0.55), Inches(3.0), Inches(0.45), [[(t, 15.5, WHITE, True, SERIF)]], space_after=0)
    txt(s, x + Inches(0.28), y + Inches(1.02), Inches(3.0), Inches(0.8), [[(d, 8.5, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=0, line_spacing=1.05)
footer(s, 4)

# ---------- 5 · Données ----------
s = slide_new(); bg(s)
kicker(s, "03 · Données & contrat", color=TEAL_DARK)
title(s, "Telecom Credit Scoring Data — le vrai jeu, pas une démo")
stats = [("500 000", "abonnés analysés (Nigeria)"), ("15", "colonnes, schéma validé"), ("70 / 10 / 20", "train / valid / test stratifié"), ("55 / 23 / 22 %", "low / medium / high")]
for i, (v, d) in enumerate(stats):
    x = Inches(1.1 + i * 2.85)
    rect(s, x, Inches(1.8), Inches(2.55), Inches(1.35), fill=WHITE, line=LINE, round_=True, radius=0.12)
    txt(s, x + Inches(0.2), Inches(1.92), Inches(2.2), Inches(0.75), [[(v, 21, NAVY, True, SANS)]], space_after=0)
    txt(s, x + Inches(0.2), Inches(2.62), Inches(2.2), Inches(0.5), [[(d, 8, MUTED, False, SANS)]], space_after=0, line_spacing=1.0)
txt(s, Inches(1.1), Inches(3.45), Inches(11), Inches(0.4), [[("Le contrat de données (validate.py) bloque l'entraînement sur des données corrompues :", 11, INK, True, SANS)]], space_after=2)
checks = [
    ("15/15 colonnes attendues", True), ("Types conformes", True), ("Plages & domaines OK", True),
    ("0 valeur manquante", True), ("Volume ≥ 10 000 lignes", True), ("13 661 doublons customer_id → avertissement (non bloquant)", False),
]
for i, (t, ok) in enumerate(checks):
    y = Inches(4.0 + i * 0.42)
    txt(s, Inches(1.35), y, Inches(0.4), Inches(0.35),
        [[("✓" if ok else "!", 13, GREEN if ok else AMBER, True, SANS)]], space_after=0)
    txt(s, Inches(1.85), y, Inches(9.5), Inches(0.35), [[(t, 10, INK if ok else RGBColor(0x92, 0x40, 0x0E), False, SANS)]], space_after=0)
footer(s, 5)

# ---------- 6 · Architecture ----------
s = slide_new(); bg(s)
kicker(s, "02 · Architecture cible", color=TEAL_DARK)
title(s, "De la donnée à la surveillance : 8 étapes, 2 référentiels")
pic(s, ARCH, Inches(1.75), max_w=Inches(11.13), max_h=Inches(4.55))
txt(s, Inches(1.1), Inches(6.35), Inches(11.1), Inches(0.4),
    [[("Une seule boucle : la surveillance reboucle sur l'entraînement — et seulement après validation humaine.", 10, MUTED, False, SANS)]], space_after=0)
footer(s, 6)

# ---------- 7 · Pipeline CI/CD/CT ----------
s = slide_new(); bg(s)
kicker(s, "02 · Pipeline", color=TEAL_DARK)
title(s, "CI · CD · CT — trois boucles, des portes à chaque étape")
pic(s, PIPELINE, Inches(1.75), max_w=Inches(11.13), max_h=Inches(3.6))
flows = [
    ("CI", "push / PR", "ruff → 32 tests → pipeline + quality gate → build + Trivy", "échec = fusion bloquée"),
    ("CD", "tag model-v*", "staging → approbation humaine → canary 10 % → 100 %", "échec = rollback auto"),
    ("CT", "nuits 03:00", "monitoring → drift → dvc repro → quality gate → PR de promotion", "jamais d'auto-production"),
]
for i, (t, trig, steps, fail) in enumerate(flows):
    x = Inches(1.1 + i * 3.85)
    rect(s, x, Inches(5.35), Inches(3.55), Inches(1.35), fill=WHITE, line=LINE, round_=True, radius=0.12)
    chip(s, x + Inches(0.22), Inches(5.5), Inches(1.05), t, fill=NAVY, color=WHITE)
    txt(s, x + Inches(1.35), Inches(5.53), Inches(2.1), Inches(0.35), [[(trig, 9, MUTED, False, SANS)]], space_after=0)
    txt(s, x + Inches(0.22), Inches(5.95), Inches(3.1), Inches(0.45), [[(steps, 8, INK, False, SANS)]], space_after=0, line_spacing=1.0)
    txt(s, x + Inches(0.22), Inches(6.38), Inches(3.1), Inches(0.3), [[(fail, 8.5, ROSE, True, SANS)]], space_after=0)
footer(s, 7)

# ---------- 8 · La chaîne livrée ----------
s = slide_new(); bg(s, NAVY_DARK)
kicker(s, "02 · La chaîne livrée", color=TEAL)
title(s, "Rejouable bit à bit, de la donnée brute au serving", color=WHITE)
pic(s, FIG_DIR / "f03_chaine_mlops.png", Inches(1.95), max_w=Inches(11.13), max_h=Inches(1.55))
rect(s, Inches(1.1), Inches(3.85), Inches(11.13), Inches(0.02), fill=NAVY_SOFT)
txt(s, Inches(1.1), Inches(4.0), Inches(11.1), Inches(0.35), [[("dvc repro — quatre étapes, qualité garantie à chaque palier :", 11, WHITE, True, SANS)]], space_after=4)
steps = [("validate", "Contrat (schéma, plages, domaines) — arrêt si règle bloquante"),
         ("preprocess", "Split stratifié 70/10/20 + 4 variables dérivées (late_rate, log_spend…)"),
         ("train", "LogReg · RandomForest · HistGBM — MLflow, best → @candidate"),
         ("evaluate", "Métriques test + quality gate → @staging")]
for i, (t, d) in enumerate(steps):
    y = Inches(4.45 + i * 0.48)
    txt(s, Inches(1.35), y, Inches(0.45), Inches(0.4), [[(str(i + 1), 13, TEAL, True, SERIF)]], space_after=0)
    txt(s, Inches(1.95), y, Inches(2.0), Inches(0.4), [[(t, 11.5, WHITE, True, SANS)]], space_after=0, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(4.1), y, Inches(8.0), Inches(0.4), [[(d, 9.5, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=0, anchor=MSO_ANCHOR.MIDDLE)
txt(s, Inches(1.1), Inches(6.5), Inches(11.1), Inches(0.35), [[("126 fichiers versionnés · 88 suivis par Git · tout le reste tracé par DVC (dvc.lock)", 9, RGBColor(0x8F, 0xB7, 0xD8), False, SANS)]], space_after=0)
footer(s, 8)

print("Slides 1–8 OK")

# ---------- 9 · Ce qui est livré ----------
s = slide_new(); bg(s)
kicker(s, "02 · Le dépôt", color=TEAL_DARK)
title(s, "Une industrialisation complète, pas une maquette")
left = [
    ("src/impayes/", "ingestion · contrat · features · train/evaluate/registry · monitoring · API"),
    ("tests/", "32 tests automatiques — tous passent"),
    ("docker/ + compose", "image API immuable + image MLflow dédiée (non-root)"),
    (".github/workflows/", "ci.yml · cd.yml · ct.yml"),
    ("monitoring/", "Prometheus + alertes + Grafana (9 panneaux)"),
    ("deploy/k8s/", "stable + canary + HPA + Ingress NGINX"),
]
for i, (t, d) in enumerate(left):
    y = Inches(1.75 + i * 0.72)
    rect(s, Inches(1.1), y, Inches(6.6), Inches(0.62), fill=WHITE, line=LINE, round_=True, radius=0.22)
    txt(s, Inches(1.32), y + Inches(0.06), Inches(6.2), Inches(0.25), [[(t, 10.5, NAVY, True, SANS)]], space_after=0)
    txt(s, Inches(1.32), y + Inches(0.28), Inches(6.2), Inches(0.28), [[(d, 8, MUTED, False, SANS)]], space_after=0)
right = [
    ("88", "fichiers versionnés Git"),
    ("32", "tests passent"),
    ("3", "algorithmes comparés"),
    ("100 %", "rejouable (dvc repro + lock)"),
    ("0", "donnée personnelle en entrée"),
]
for i, (v, d) in enumerate(right):
    y = Inches(1.75 + i * 0.9)
    rect(s, Inches(8.05), y, Inches(4.2), Inches(0.78), fill=NAVY, round_=True, radius=0.14)
    txt(s, Inches(8.3), y + Inches(0.07), Inches(2.0), Inches(0.65), [[(v, 22, TEAL, True, SANS)]], space_after=0)
    txt(s, Inches(8.3), y + Inches(0.46), Inches(3.6), Inches(0.28), [[(d, 7.5, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=0)
footer(s, 9)

# ---------- 10 · Entraînement ----------
s = slide_new(); bg(s)
kicker(s, "04 · Entraînement", color=TEAL_DARK)
title(s, "Trois algorithmes comparés — la logistique gagne")
from pptx.chart.data import CategoryChartData
chart_data = CategoryChartData()
chart_data.categories = ["LogReg", "RandomForest", "HistGBM"]
chart_data.add_series("F1-macro (validation)", (0.4697, 0.4528, 0.4575))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1.1), Inches(1.8), Inches(6.1), Inches(4.3), chart_data)
chart = gf.chart
chart.has_legend = False
chart.has_title = False
plot = chart.plots[0]
plot.gap_width = 80
series = plot.series[0]
for i, pt in enumerate(series.points):
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = TEAL if i == 0 else RGBColor(0x9F, 0xB3, 0xC8)
val_axis = chart.value_axis
val_axis.maximum_scale = 0.55
val_axis.minimum_scale = 0.0
val_axis.has_major_gridlines = True
cat_axis = chart.category_axis
txt(s, Inches(1.1), Inches(6.15), Inches(6.1), Inches(0.3),
    [[("F1-macro validation — graine 42, class_weight=balanced", 8.5, MUTED, False, SANS)]],
    align=PP_ALIGN.CENTER, space_after=0)
cmp_rows = [("LogReg", "0,470", "0,673", "0,650", "0,9 s", True),
            ("RandomForest", "0,453", "0,668", "0,650", "10,2 s", False),
            ("HistGradientBoosting", "0,457", "0,667", "0,648", "2,1 s", False)]
x0 = Inches(7.55)
tbl = s.shapes.add_table(4, 5, x0, Inches(1.9), Inches(4.7), Inches(1.7)).table
headers = ["Candidat", "F1", "Rappel·high", "AUC", "Train"]
for j, h in enumerate(headers):
    cell = tbl.cell(0, j)
    cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
    txt_cell(cell, [(h, 9, WHITE, True, SANS)])
for i, row in enumerate(cmp_rows):
    is_best = row[5]
    for j, v in enumerate(row[:5]):
        cell = tbl.cell(i + 1, j)
        cell.fill.solid(); cell.fill.fore_color.rgb = TEAL_PALE if is_best else WHITE
        bold = is_best and j < 2
        txt_cell(cell, [(str(v), 9, INK, bold, SANS)])
rect(s, Inches(7.55), Inches(4.0), Inches(4.7), Inches(2.3), fill=WHITE, line=LINE, round_=True, radius=0.14)
txt(s, Inches(7.8), Inches(4.12), Inches(4.3), Inches(0.35),
    [[("Pourquoi LogReg ?", 13, NAVY, True, SERIF)]], space_after=4)
reasons = ["Explicable : coefficients lisibles par l'audit", "0,9 s à entraîner — CT quotidien viable",
           "2 Ko de coefficients — la démo tient en JavaScript", "Le boost n'apportait rien (AUC équivalente)"]
for i, t in enumerate(reasons):
    txt(s, Inches(7.8), Inches(4.62 + i * 0.42), Inches(4.3), Inches(0.4), [[("·  ", 10, TEAL_DARK, True, SANS), (t, 8.5, INK, False, SANS)]], space_after=0, line_spacing=1.0)
footer(s, 10)

# ---------- 11 · Résultats réels ----------
s = slide_new(); bg(s)
kicker(s, "05 · Résultats", color=TEAL_DARK)
title(s, "Les vrais chiffres, sur 100 000 abonnés jamais vus")
kpis = [("0,469", "F1-macro (test)", "gate ≥ 0,45 ✓", TEAL_DARK),
        ("0,674", "Rappel « high »", "gate ≥ 0,60 ✓", TEAL_DARK),
        ("0,650", "AUC one-vs-rest", "proche du hasard, mais utile", NAVY_MID),
        ("1,54 ms", "Latence p95", "gate ≤ 150 ms ✓", TEAL_DARK)]
for i, (v, lab, sub, accent) in enumerate(kpis):
    kpi_card(s, Inches(1.1 + i * 2.87), Inches(1.8), Inches(2.6), Inches(1.75), v, lab, sub, accent)
rect(s, Inches(1.1), Inches(3.85), Inches(11.13), Inches(2.6), fill=WHITE, line=LINE, round_=True, radius=0.1)
txt(s, Inches(1.35), Inches(4.0), Inches(6.0), Inches(0.35), [[("Quality gate — 4/4 conditions", 12.5, NAVY, True, SERIF)]], space_after=6)
gate = [("F1-macro ≥ 0,45", "0,469"), ("Rappel « high » ≥ 0,60", "0,674"),
        ("Latence p95 ≤ 150 ms", "1,54 ms"), ("Non-régression vs production", "v1 d'abord en production")]
for i, (t, v) in enumerate(gate):
    x = Inches(1.35 + (i % 2) * 5.45); y = Inches(4.55 + (i // 2) * 0.85)
    txt(s, x, y, Inches(4.6), Inches(0.3),
        [[("✓ ", 12, GREEN, True, SANS), (t, 10.5, INK, False, SANS)]], space_after=0)
    txt(s, x + Inches(0.42), y + Inches(0.26), Inches(4.2), Inches(0.3),
        [[(v, 9.5, TEAL_DARK, True, SANS)]], space_after=0)
rect(s, Inches(1.1), Inches(6.55), Inches(11.13), Inches(0.02), fill=LINE)
txt(s, Inches(1.1), Inches(6.62), Inches(11.1), Inches(0.35),
    [[("Référence vs majorité « low » : accuracy 0,582 vs 0,546 — le modèle sait quand dire « high ».", 9, MUTED, False, SANS)]], space_after=0)
footer(s, 11)

# ---------- 12 · Matrice de confusion ----------
s = slide_new(); bg(s)
kicker(s, "05 · Analyse des erreurs", color=TEAL_DARK)
title(s, "La classe « medium » concentre la confusion — comme prévu")
cm = M["confusion_matrix"]["matrix"]
labels = M["confusion_matrix"]["labels"]
row_sums = [sum(r) for r in cm]
maxv = max(max(r) for r in cm)
tbl = s.shapes.add_table(4, 4, Inches(1.1), Inches(1.9), Inches(6.3), Inches(3.1)).table
tbl.columns[0].width = Inches(1.35)
for j, lab in enumerate(["réel ↓ · prédit →"] + labels):
    cell = tbl.cell(0, j)
    cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
    txt_cell(cell, [(lab, 9.5, WHITE, True, SANS)], align=PP_ALIGN.CENTER if j else PP_ALIGN.LEFT)
for i, row in enumerate(cm):
    cell = tbl.cell(i + 1, 0)
    cell.fill.solid(); cell.fill.fore_color.rgb = PAPER
    txt_cell(cell, [(labels[i], 10.5, NAVY, True, SANS)])
    for j, v in enumerate(row):
        cell = tbl.cell(i + 1, j + 1)
        alpha_val = 0.12 + 0.75 * (v / maxv)
        base = TEAL if i == j else ROSE
        tint = RGBColor(int(base[0] * alpha_val + 255 * (1 - alpha_val)),
                        int(base[1] * alpha_val + 255 * (1 - alpha_val)),
                        int(base[2] * alpha_val + 255 * (1 - alpha_val)))
        cell.fill.solid(); cell.fill.fore_color.rgb = tint
        txt_cell(cell, [(f"{v:,.0f}".replace(",", " "), 10, INK if alpha_val > 0.35 else MUTED, True, SANS)],
                  align=PP_ALIGN.CENTER)
rect(s, Inches(8.15), Inches(1.9), Inches(4.1), Inches(3.1), fill=WHITE, line=LINE, round_=True, radius=0.14)
txt(s, Inches(8.4), Inches(2.02), Inches(3.6), Inches(0.35), [[("Ce que ça raconte", 13, NAVY, True, SERIF)]], space_after=6)
readings = [
    ("« high » détecté 15 000 fois", "sur 22 258 réels (rappel 0,67)"),
    ("« medium » oublié 86 % du temps", "classe intermédiaire, par nature dure"),
    ("« low » bien servi", "accuracy 0,58 — filtre utile pour l'octroi"),
]
for i, (t, d) in enumerate(readings):
    y = Inches(2.55 + i * 0.78)
    txt(s, Inches(8.4), y, Inches(3.7), Inches(0.3), [[(t, 9.5, INK, True, SANS)]], space_after=0)
    txt(s, Inches(8.4), y + Inches(0.24), Inches(3.7), Inches(0.3), [[(d, 8.5, MUTED, False, SANS)]], space_after=0)
rect(s, Inches(1.1), Inches(5.35), Inches(11.13), Inches(1.1), fill=RGBColor(0xFF, 0xFB, 0xEB), round_=True, radius=0.1)
rect(s, Inches(1.1), Inches(5.35), Inches(0.12), Inches(1.1), fill=AMBER)
txt(s, Inches(1.3), Inches(5.42), Inches(10.7), Inches(0.3), [[("Honnêteté méthodologique", 10, RGBColor(0x92, 0x40, 0x0E), True, SANS)]], space_after=1)
txt(s, Inches(1.3), Inches(5.7), Inches(10.7), Inches(0.65),
    [[("La réplique synthétique (développement) donnait 0,649 de F1-macro — le vrai jeu nigérian est beaucoup plus dur. Les chiffres du rapport sont donc à régénérer ; le pipeline l'a fait. La chaîne, elle, était déjà prête.", 8.5, RGBColor(0x92, 0x40, 0x0E), False, SANS)]],
    space_after=0, line_spacing=1.05)
footer(s, 12)

# ---------- 13 · Registre MLflow ----------
s = slide_new(); bg(s)
kicker(s, "06 · Registre & traçabilité", color=TEAL_DARK)
title(s, "Du notebook… au registre MLflow, version par version")
pic(s, FIG_DIR / "f06_cycle_vie.png", Inches(1.85), max_w=Inches(11.13), max_h=Inches(1.5))
txt(s, Inches(1.1), Inches(3.55), Inches(11), Inches(0.35), [[("Version 1 — livrée et auditée :", 11, INK, True, SANS)]], space_after=4)
trace_rows = [
    ("candidate", "train.py", "F1-val 0,470 · AUC 0,650 · gate OK"),
    ("staging", "evaluate.py", "F1-test 0,469 · rappel high 0,674 · p95 1,54 ms"),
    ("production", "merge « DONGMO WOZE Junior »", "18/11/2026 — 23:53 UTC · journal d'audit jsonl"),
]
for i, (a, who, what) in enumerate(trace_rows):
    y = Inches(4.05 + i * 0.62)
    chip(s, Inches(1.1), y, Inches(1.7), a, fill=NAVY if i == 2 else PAPER, color=WHITE if i == 2 else NAVY)
    txt(s, Inches(2.95), y, Inches(3.4), Inches(0.4), [[(who, 9.5, MUTED, False, SANS)]], anchor=MSO_ANCHOR.MIDDLE, space_after=0)
    txt(s, Inches(6.3), y, Inches(5.9), Inches(0.4), [[(what, 9.5, INK, False, SANS)]], anchor=MSO_ANCHOR.MIDDLE, space_after=0)
footer(s, 13)

# ---------- 14 · API & Docker ----------
s = slide_new(); bg(s)
kicker(s, "06 · Serving", color=TEAL_DARK)
title(s, "Une API qui ne boude personne — même sans Python installé")
endpoints = [("POST /predict", "prédiction unitaire — 422 si entrée invalide"),
             ("POST /predict/batch", "lot ≤ 1000 clients — campagne mensuelle"),
             ("POST /feedback", "impayé constaté → concept drift"),
             ("GET /health · /model-info", "sonde de vie — version du modèle servie"),
             ("GET /metrics", "métriques Prometheus (latence, classes)")]
for i, (ep, d) in enumerate(endpoints):
    y = Inches(1.75 + i * 0.62)
    rect(s, Inches(1.1), y, Inches(6.5), Inches(0.54), fill=WHITE, line=LINE, round_=True, radius=0.25)
    txt(s, Inches(1.32), y + Inches(0.05), Inches(6.1), Inches(0.2), [[(ep, 9.5, TEAL_DARK, True, SANS)]], space_after=0)
    txt(s, Inches(1.32), y + Inches(0.26), Inches(6.1), Inches(0.22), [[(d, 7.5, MUTED, False, SANS)]], space_after=0)
rect(s, Inches(7.85), Inches(1.75), Inches(4.35), Inches(5.05), fill=NAVY, round_=True, radius=0.1)
txt(s, Inches(8.1), Inches(1.95), Inches(4.0), Inches(0.35), [[("Le bug trouvé en vérifiant", 12, AMBER, True, SERIF)]], space_after=6)
txt(s, Inches(8.1), Inches(2.4), Inches(3.9), Inches(2.4),
    [[("L'image Docker ne démarrait pas : config.py déduisait la racine du projet du chemin du paquet installé (site-packages en image) — FileNotFoundError: params.yaml.", 9, WHITE, False, SANS)],
     [("Corrigé : la racine retombe sur le répertoire courant (/app en image). Vérifié : conteneur boot → /health 200 → smoke tests OK.", 9, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]],
    space_after=6, line_spacing=1.1)
rect(s, Inches(8.1), Inches(4.9), Inches(3.85), Pt(0.75), fill=NAVY_SOFT)
txt(s, Inches(8.1), Inches(5.02), Inches(3.9), Inches(0.3), [[("La leçon : build ≠ run", 9.5, TEAL, True, SANS)]], space_after=1)
txt(s, Inches(8.1), Inches(5.34), Inches(3.9), Inches(1.2),
    [[("La CI buildait l'image sans jamais la lancer. Ajouté au backlog : smoke test du conteneur en CI.", 8.5, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=0, line_spacing=1.1)
footer(s, 14)

# ---------- 15 · CI/CD/CT ----------
s = slide_new(); bg(s)
kicker(s, "07 · CI/CD/CT en pratique", color=TEAL_DARK)
title(s, "Le pipeline humain au centre — la machine exécute, l'humain décide")
pic(s, FIG_DIR / "f05_canary.png", Inches(1.9), max_w=Inches(11.13), max_h=Inches(1.6))
rows = [
    ("CI", "Chaque push / PR", "ruff → 32 tests → dvc repro → gate → Docker build + Trivy", "merge bloqué si rouge"),
    ("CD", "Tag model-v* ou manuel", "image → staging → smoke tests → approbation humaine → canary 10 % → 100 %", "rollback auto si critères KO"),
    ("CT", "Tous les jours · 03:00 UTC", "monitoring PSI/KS/F1 → dvc repro si dérive confirmée → PR de promotion", "jamais de remplacement auto"),
]
for i, (t, when, steps, fail) in enumerate(rows):
    y = Inches(3.75 + i * 0.95)
    chip(s, Inches(1.1), y, Inches(0.9), t, fill=NAVY, color=WHITE)
    txt(s, Inches(2.2), y, Inches(3.2), Inches(0.35), [[(when, 9.5, NAVY, True, SANS)]], space_after=0)
    txt(s, Inches(2.2), y + Inches(0.28), Inches(9.9), Inches(0.35), [[(steps, 9, INK, False, SANS)]], space_after=0)
    txt(s, Inches(2.2), y + Inches(0.52), Inches(9.9), Inches(0.25), [[(fail, 8.5, ROSE, True, SANS)]], space_after=0)
footer(s, 15)

# ---------- 16 · Monitoring ----------
s = slide_new(); bg(s)
kicker(s, "07 · Surveillance", color=TEAL_DARK)
title(s, "La dérive est un signal d'alerte — jamais un ordre de remplacement")
pic(s, FIG_DIR / "f04_drifts.png", Inches(1.8), max_w=Inches(11.13), max_h=Inches(2.35))
pic(s, FIG_DIR / "f07_niveaux_monitoring.png", Inches(4.3), max_w=Inches(11.13), max_h=Inches(1.9))
txt(s, Inches(1.1), Inches(6.28), Inches(11.1), Inches(0.75),
    [[("Semaines 5–8 : l'inflation fait dériver les dépenses (PSI jusqu'à 0,71) — le F1 reste stable : ", 9.5, INK, False, SANS),
       ("analyse, pas de réentraînement. ", 9.5, INK, True, SANS),
       ("Semaine 10 : le concept drift est confirmé (F1 0,408) → CT déclenché.", 9.5, TEAL_DARK, True, SANS)]],
    space_after=0, line_spacing=1.15)
footer(s, 16)

# ---------- 17 · Le produit ----------
s = slide_new(); bg(s, NAVY_DARK)
kicker(s, "08 · Le produit", color=TEAL)
title(s, "Un produit « vendable » — qui tourne sans aucune installation", color=WHITE)
tiers = [
    ("Navigateur seul", "demo/index.html", "90 Ko · 100 % hors-ligne · Windows / Mac / Linux", "le jury double-clique et voit l'IA tourner"),
    ("Exécutable autonome", "NaijaTel-ImpayesAI-Demo.app", "7,6 Mo · PyInstaller · zéro Python requis", "le commercial part avec une clé USB"),
    ("API + Docker", "impayes-api · impayes-mlflow", "compose up -d · CI/CD/CT prêts pour GHCR + k8s", "l'entreprise déploie dans son cluster"),
]
for i, (t, sub, spec, usage) in enumerate(tiers):
    y = Inches(1.9 + i * 1.35)
    rect(s, Inches(1.1), y, Inches(11.13), Inches(1.15), fill=NAVY, round_=True, radius=0.12)
    rect(s, Inches(1.1), y, Inches(0.14), Inches(1.15), fill=TEAL)
    txt(s, Inches(1.4), y + Inches(0.1), Inches(4.6), Inches(0.35), [[(t, 14, WHITE, True, SERIF)]], space_after=0)
    txt(s, Inches(1.4), y + Inches(0.45), Inches(4.6), Inches(0.3), [[(sub, 8.5, TEAL, False, SANS)]], space_after=0)
    txt(s, Inches(6.2), y + Inches(0.08), Inches(5.9), Inches(0.35), [[(spec, 9, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=0)
    txt(s, Inches(6.2), y + Inches(0.5), Inches(5.9), Inches(0.35), [[(usage, 8.5, RGBColor(0x8F, 0xB7, 0xD8), False, SANS)]], space_after=0)
footer(s, 17)

# ---------- 18 · Traçabilité ----------
s = slide_new(); bg(s)
kicker(s, "08 · De la requête au commit", color=TEAL_DARK)
title(s, "Chaque décision est explicable — bout en bout")
chain = [
    ("request_id", "journalisé dans predictions.jsonl (sans PII)"),
    ("réponse API", "probabilités + model_version (v1)"),
    ("run MLflow", "2805ad80… — paramètres, métriques, artefacts"),
    ("commit Git", "03bb77f — code du pipeline"),
    ("empreinte DVC", "517425048d… — version exacte des données"),
    ("dvc.lock", "rejouable bit à bit par le jury (dvc repro)"),
]
for i, (t, d) in enumerate(chain):
    y = Inches(1.8 + i * 0.68)
    oval(s, Inches(1.15), y, Inches(0.5), Inches(0.5), fill=TEAL)
    txt(s, Inches(1.15), y + Inches(0.08), Inches(0.5), Inches(0.3), [[(str(i + 1), 12, NAVY_DARK, True, SANS)]],
        align=PP_ALIGN.CENTER, space_after=0)
    if i < len(chain) - 1:
        rect(s, Inches(1.36), y + Inches(0.52), Inches(0.08), Inches(0.22), fill=TEAL)
    txt(s, Inches(1.9), y + Inches(0.02), Inches(3.0), Inches(0.45), [[(t, 11.5, NAVY, True, SANS)]], space_after=0, anchor=MSO_ANCHOR.MIDDLE)
    txt(s, Inches(5.1), y + Inches(0.02), Inches(6.9), Inches(0.45), [[(d, 9.5, MUTED, False, SANS)]], space_after=0, anchor=MSO_ANCHOR.MIDDLE)
footer(s, 18)

# ---------- 19 · Gouvernance ----------
s = slide_new(); bg(s)
kicker(s, "08 · Gouvernance", color=TEAL_DARK)
title(s, "Un modèle de crédit n'existe pas sans règles")
rules = [
    ("Aucune donnée personnelle", "téléphone et customer_id exclus du modèle et des journaux — référence opaque"),
    ("Pas de fuite d'information", "credit_score, loan_eligibility exclus — documenté dans docs/data_preprocessing.md"),
    ("Approbation humaine", "aucune promotion automatique — approbation de la Direction du risque ou PR"),
    ("Rollback immédiat", "alias previous_production, réattribution du trafic en quelques secondes"),
    ("Journal d'audit", "reports/registry_audit.jsonl — qui a promu quoi, quand et pourquoi"),
    ("NDPR & RGPD", "base légale documentée, conservation 13 mois des journaux de prédiction"),
]
for i, (t, d) in enumerate(rules):
    x = Inches(1.1 + (i % 2) * 5.7); y = Inches(1.75 + (i // 2) * 1.5)
    rect(s, x, y, Inches(5.35), Inches(1.3), fill=WHITE, line=LINE, round_=True, radius=0.14)
    txt(s, x + Inches(0.3), y + Inches(0.18), Inches(4.8), Inches(0.35), [[("◆  ", 11, TEAL, True, SANS), (t, 11.5, NAVY, True, SANS)]], space_after=3)
    txt(s, x + Inches(0.3), y + Inches(0.55), Inches(4.8), Inches(0.65), [[(d, 8.5, MUTED, False, SANS)]], space_after=0, line_spacing=1.1)
footer(s, 19)

# ---------- 20 · Limites & prolongements ----------
s = slide_new(); bg(s)
kicker(s, "08 · Limites", color=TEAL_DARK)
title(s, "Ce que nous savons que nous ne savons pas")
current = [
    "La classe « medium » est quasi inaudible (rappel 0,09) — l'intermédiaire par nature",
    "AUC 0,65 : le modèle classe, mais sans marge écrasante",
    "13 661 doublons customer_id (2,7 %) — à purifier avant la prod",
    "Le parquet 16,8 Mo n'est pas dans Git — DVC gère (choix normal)",
    "Les chiffres du rapport doivent être régénérés (déjà fait dans reports/)",
]
nexts = [
    ("Calibration des probabilités", "seuils orientés coût métier : un impayé manqué ≠ un client refusé à tort"),
    ("A/B test réel 30 jours", "les impayés mettent 30–60 jours à se constater — le canary seul ne suffit pas"),
    ("Features métier", "ratios plutôt que montants bruts — robustesse à l'inflation du naira"),
    ("Explication locale", "SHAP/LIME par prédiction — explicable devant le régulateur"),
    ("Onboarding 2 semaines", "une agence partenaire, 3 mois de données, go / no-go à la clé"),
]
txt(s, Inches(1.1), Inches(1.75), Inches(5.5), Inches(0.4), [[("Limites assumées", 13, ROSE, True, SERIF)]], space_after=6)
for i, t in enumerate(current):
    y = Inches(2.3 + i * 0.72)
    txt(s, Inches(1.2), y, Inches(5.3), Inches(0.68), [[("✕  ", 11, ROSE, True, SANS), (t, 8.5, INK, False, SANS)]], space_after=0, line_spacing=1.1)
txt(s, Inches(7.35), Inches(1.75), Inches(4.9), Inches(0.4), [[("Prolongements proposés", 13, TEAL_DARK, True, SERIF)]], space_after=6)
for i, (t, d) in enumerate(nexts):
    y = Inches(2.3 + i * 0.72)
    txt(s, Inches(7.4), y, Inches(4.8), Inches(0.3), [[(f"0{i+1}.  ", 10, TEAL_DARK, True, SANS), (t, 9, NAVY, True, SANS)]], space_after=1)
    txt(s, Inches(7.95), y + Inches(0.22), Inches(4.3), Inches(0.45), [[(d, 8, MUTED, False, SANS)]], space_after=0, line_spacing=1.0)
footer(s, 20)

# ---------- 21 · Plan de travail (soutenance) ----------
s = slide_new(); bg(s)
kicker(s, "Plan de travail", color=TEAL_DARK)
title(s, "À J moins 7 — le plan tient en une semaine")
plan = [
    ("J-7", "Geler le code", "tag stable · zip USB ×2 · vérifier la démo sur Windows/Mac", "MBONGO"),
    ("J-5", "Répéter en duo", "3 runs complets · chronomètre 20 min · relais MBONGO→DONGMO", "Ensemble"),
    ("J-3", "Répéter sans slides", "raconter le projet de mémoire — 10 min story · 10 min démo", "Ensemble"),
    ("J-1", "Test salle", "projecteur 16:9 · présentateur · clé USB bootée · WiFi coupé volontairement", "DONGMO"),
    ("J0", "20 minutes live", "00:00 MBONGO · 02:00 architecture/pipeline DONGMO · 05:00 résultats · 08:00 registry/CI · 11:00 DÉMO · 15:00 gouvernance · 17:00 conclusion", "Tous"),
]
for i, (d, t, det, who) in enumerate(plan):
    y = Inches(1.8 + i * 0.85)
    chip(s, Inches(1.1), y, Inches(0.95), d, fill=NAVY, color=WHITE)
    txt(s, Inches(2.35), y, Inches(2.6), Inches(0.3), [[(t, 10, NAVY, True, SANS)]], space_after=1)
    txt(s, Inches(2.35), y + Inches(0.24), Inches(7.4), Inches(0.5), [[(det, 8.5, MUTED, False, SANS)]], space_after=0, line_spacing=1.05)
    chip(s, Inches(10.35), y + Inches(0.08), Inches(1.85), who, fill=PAPER, color=NAVY)
footer(s, 21)

# ---------- 22 · Binôme & méthode ----------
s = slide_new(); bg(s)
kicker(s, "Organisation", color=TEAL_DARK)
title(s, "Deux volets, une mise en commun — la méthode compte")
duo = [
    ("MBONGO BOLLO Jarle Wulfrid", "Données & modèle", "R1–R5 · R9 · chaîne données/DVC · entraînement MLflow · monitoring & simulation · résultats", "00:00 – 05:00  ·  11:00 – 15:00"),
    ("DONGMO WOZE Junior", "Industrialisation", "R6–R10 · API FastAPI · Docker · CI/CD/CT GitHub Actions · registre/promotion · Prometheus/Grafana · gouvernance", "05:00 – 08:00  ·  08:00 – 11:00"),
    ("Ensemble", "Le projet commun", "Architecture cible · choix des outils · rapport & présentation · soutenance", "Q&A — réponses croisées"),
]
for i, (n, role, detail, slot) in enumerate(duo):
    y = Inches(1.8 + i * 1.45)
    rect(s, Inches(1.1), y, Inches(11.13), Inches(1.3), fill=WHITE, line=LINE, round_=True, radius=0.12)
    rect(s, Inches(1.1), y, Inches(0.14), Inches(1.3), fill=TEAL)
    txt(s, Inches(1.5), y + Inches(0.16), Inches(6.0), Inches(0.4), [[(n, 13.5, NAVY, True, SERIF)]], space_after=1)
    chip(s, Inches(1.5), y + Inches(0.53), Inches(2.0), role, fill=TEAL_PALE, color=TEAL_DARK)
    txt(s, Inches(1.5), y + Inches(0.95), Inches(10.5), Inches(0.3), [[(detail, 8, MUTED, False, SANS)]], space_after=0)
    txt(s, Inches(8.6), y + Inches(0.14), Inches(3.3), Inches(0.22), [[("CRÉNEAU", 7, MUTED, True, SANS)]], align=PP_ALIGN.RIGHT, space_after=0)
    txt(s, Inches(8.6), y + Inches(0.36), Inches(3.3), Inches(0.3), [[(slot, 8.5, TEAL_DARK, True, SANS)]], align=PP_ALIGN.RIGHT, space_after=0)
footer(s, 22)

# ---------- 23 · Antisèche jury ----------
s = slide_new(); bg(s, NAVY_DARK)
kicker(s, "Annexe — antisèche jury", color=TEAL)
title(s, "Les six questions qui vont tomber — avec les réponses", color=WHITE)
qa = [
    ("Q. Le F1 réel est très bas, non ?", "Oui — 0,469 sur le vrai jeu (le 0,88 du sujet est un scénario pédagogique ; la réplique synthétique donnait 0,649). Le modèle est utile, pas définitif : l'erreur « medium » est documentée, les prolongements sont identifiés."),
    ("Q. Pourquoi pas HistGradientBoosting ?", "F1-val 0,457 < 0,470 pour LogReg, 2,3 s de plus, 900× plus lourd en mémoire et 2 Ko de coefficients — idéal pour la démo hors-ligne en JavaScript."),
    ("Q. Le registre MLflow sert vraiment à quelque chose ?", "Oui : candidate → staging → production avec approbation humaine, journal d'audit jsonl, promotion tracée par nom, rollback instantané (alias previous_production)."),
    ("Q. Que se passe-t-il si le modèle dérive ?", "PSI/KS quotidien + F1 sur impayés constatés ; au-delà des seuils : alerte → analyse → réentraînement conditionnel via CT — jamais de remplacement automatique (R10.3)."),
    ("Q. La latence p95 = 1,5 ms, réaliste ?", "Oui, sur données locales : LogReg = produit scalaire. La charge réelle dépendra de l'infra — d'où le HPA k8s et le suivi Prometheus en continu."),
    ("Q. Le projet est-il déployable demain ?", "Oui pour un pilote : docker compose up -d, tests de fumée, canary 10 % prévu, rollback en quelques secondes. Il manque l'onboarding d'un partenaire pilote."),
]
for i, (q, a) in enumerate(qa):
    y = Inches(1.7 + i * 0.82)
    rect(s, Inches(1.1), y, Inches(11.13), Inches(0.72), fill=NAVY, round_=True, radius=0.18)
    txt(s, Inches(1.35), y + Inches(0.07), Inches(10.6), Inches(0.25), [[(q, 9.5, AMBER, True, SANS)]], space_after=1)
    txt(s, Inches(1.35), y + Inches(0.3), Inches(10.6), Inches(0.38), [[(a, 8, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=0, line_spacing=1.05)
footer(s, 23)

# ---------- 24 · Questions & merci ----------
s = slide_new(); bg(s, NAVY_DARK)
rect(s, 0, Inches(3.35), prs.slide_width, Inches(0.045), fill=TEAL)
txt(s, Inches(1.1), Inches(1.1), Inches(11), Inches(1.6), [
    [("Et maintenant —", 20, TEAL, False, SERIF)],
    [("vos questions.", 52, WHITE, True, SERIF)],
], space_after=2)
txt(s, Inches(1.1), Inches(4.6), Inches(11.2), Inches(0.4),
    [[("Dépôt : github.com/Logan1xl/mlops-impayes-telecom · branche feature/demo-soutenance", 11, RGBColor(0xBC, 0xD4, 0xEA), False, SANS)]], space_after=2)
txt(s, Inches(1.1), Inches(5.1), Inches(11.2), Inches(0.4),
    [[("Démo live : abrir demo/index.html — ou NaijaTel-ImpayesAI-Demo.app (aucune installation)", 11, RGBColor(0x8F, 0xB7, 0xD8), False, SANS)]], space_after=2)
txt(s, Inches(1.1), Inches(5.6), Inches(11.2), Inches(0.4),
    [[("Merci — MBONGO BOLLO Jarle Wulfrid · DONGMO WOZE Junior — Dr KUATE Alain François, encadrant", 11, AMBER, True, SANS)]], space_after=0)

TOTAL = len(prs.slides.__iter__.__self__._sldIdLst)  # informatif seulement
prs.save(str(OUT))
print(f"Présentation enregistrée : {OUT}")
