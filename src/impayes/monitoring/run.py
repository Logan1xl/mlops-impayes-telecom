"""Job de monitoring (exécuté quotidiennement par le pipeline CT).

  python -m impayes.monitoring.run batch      # analyse les prédictions réelles loguées par l'API
  python -m impayes.monitoring.run simulate   # scénario de 12 semaines avec dérive (démonstration)

Sorties : reports/monitoring/*.json, figures et un tableau de bord HTML
autonome (reports/monitoring/dashboard.html).
Code de sortie 3 si la règle de décision demande un réentraînement : le
workflow GitHub Actions « ct.yml » s'en sert pour lancer l'entraînement.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from impayes.config import load_params, path  # noqa: E402
from impayes.data import synthetic  # noqa: E402
from impayes.features.build_features import input_columns  # noqa: E402
from impayes.monitoring.drift import analyse  # noqa: E402
from impayes.plotting import PALETTE, style_axes, use_report_style  # noqa: E402

use_report_style()

log = logging.getLogger("impayes.monitoring")
OUT = path("reports/monitoring")

# Scénario : semaines 1-4 stables ; 5-8 inflation (dépenses x1.2 puis x1.6) ;
# 9-12 crise -> plus de retards et relation retards/impayés renforcée.
SCENARIO = [
    {"week": w, "spend": s, "late": lt, "concept": c, "load": ld}
    for w, s, lt, c, ld in [
        (1, 1.00, 0.0, 0.0, 1.0), (2, 1.00, 0.0, 0.0, 1.0), (3, 1.02, 0.0, 0.0, 1.1), (4, 1.03, 0.0, 0.0, 1.2),
        (5, 1.20, 0.1, 0.0, 1.6), (6, 1.35, 0.2, 0.1, 2.2), (7, 1.50, 0.3, 0.25, 3.5), (8, 1.60, 0.5, 0.45, 5.5),
        (9, 1.65, 0.7, 0.65, 9.0), (10, 1.70, 0.9, 0.8, 14.0), (11, 1.70, 1.0, 0.95, 20.0), (12, 1.75, 1.1, 1.1, 26.0),
    ]
]


def _img(fig_path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(fig_path.read_bytes()).decode()


def measure_latency(model, X: pd.DataFrame, n: int = 120) -> np.ndarray:
    rows = X.sample(n, random_state=0)
    t = []
    for i in range(n):
        t0 = time.perf_counter()
        model.predict_proba(rows.iloc[[i]])
        t.append((time.perf_counter() - t0) * 1000)
    return np.array(t)


def simulate() -> list[dict]:
    p = load_params()
    model = joblib.load(path("models/model.joblib"))
    cols, target = input_columns(), p["data"]["target"]
    ref = pd.read_parquet(path("data/reference/reference.parquet"))
    ref_pred = pd.Series(model.predict(ref[cols]))
    metrics = json.loads(path("reports/metrics.json").read_text())
    f1_ref = metrics["f1_macro"]
    base_lat = measure_latency(model, ref[cols])

    timeline = []
    for s in SCENARIO:
        batch = synthetic.generate(8000, seed=1000 + s["week"], spend_shift=s["spend"],
                                   late_shift=s["late"], concept_shift=s["concept"])
        pred = pd.Series(model.predict(batch[cols]))
        # Latence observée = latence modèle mesurée x facteur de charge simulé (montée en volume)
        rng = np.random.default_rng(s["week"])
        lat = base_lat * s["load"] * rng.lognormal(0, 0.15, len(base_lat)) + 8 * s["load"]
        rep = analyse(ref[cols], batch[cols], ref_pred=ref_pred, cur_pred=pred,
                      f1_reference=f1_ref, y_true=batch[target], latency_ms=lat)
        row = {"week": s["week"], **{k: v for k, v in rep.to_dict().items() if k != "features"},
               "psi": {f.feature: f.psi for f in rep.features},
               "share_high_pred": float((pred == "high").mean()),
               "share_high_true": float((batch[target] == "high").mean()),
               "mean_spend": float(batch["avg_monthly_spend_ngn"].mean())}
        timeline.append(row)
        log.info("S%02d data=%-8s concept=%-8s ops=%-8s F1=%.3f -> %s", s["week"], rep.data_drift,
                 rep.concept_drift, rep.operational, rep.f1_current or float("nan"), rep.decision)
    return timeline


def plot_timeline(tl: list[dict]) -> dict[str, Path]:
    p = load_params()["monitoring"]
    OUT.mkdir(parents=True, exist_ok=True)
    weeks = [r["week"] for r in tl]
    figs = {}

    # 1) PSI par variable
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    feats = list(tl[0]["psi"].keys())
    colors = ["#1F4E79", "#C55A11", "#548235", "#7030A0", "#C00000", "#8EA9C1", "#BF9000"]
    for f, c in zip(feats, colors, strict=False):
        ax.plot(weeks, [r["psi"][f] for r in tl], marker="o", ms=3.5, lw=1.8, color=c, label=f)
    ax.axhline(p["psi_warning"], ls="--", lw=1, color=PALETTE["warn"])
    ax.axhline(p["psi_critical"], ls="--", lw=1, color=PALETTE["crit"])
    ax.text(12.25, p["psi_warning"], "alerte", va="center", fontsize=8, color=PALETTE["warn"])
    ax.text(12.25, p["psi_critical"], "critique", va="center", fontsize=8, color=PALETTE["crit"])
    ax.set_xlim(0.5, 13.3)
    ax.set_xlabel("Semaine de production")
    ax.set_ylabel("PSI")
    ax.set_title("Data drift : PSI par variable vs référence d'entraînement", loc="left",
                 fontsize=11.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper left")
    ax.set_xticks(weeks)
    style_axes(ax)
    fig.tight_layout()
    figs["psi"] = OUT / "psi_timeline.png"
    fig.savefig(figs["psi"], dpi=180)
    plt.close(fig)

    # 2) Performance réelle
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    f1 = [r["f1_current"] for r in tl]
    ref = tl[0]["f1_reference"]
    ax.plot(weeks, f1, marker="o", lw=2.2, color=PALETTE["primary"], label="F1-macro sur labels réels")
    ax.axhline(ref, color="#64748b", lw=1, label=f"F1 de référence (test) = {ref:.3f}")
    ax.axhspan(ref - p["f1_drop_critical"], ref - p["f1_drop_warning"], color=PALETTE["warn"], alpha=0.12)
    ax.axhspan(0, ref - p["f1_drop_critical"], color=PALETTE["crit"], alpha=0.08)
    ax.set_ylim(max(0, min(f1) - 0.08), ref + 0.05)
    ax.set_xticks(weeks)
    ax.set_xlabel("Semaine de production")
    ax.set_title("Concept drift : performance mesurée sur les impayés constatés", loc="left",
                 fontsize=11.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    style_axes(ax)
    fig.tight_layout()
    figs["f1"] = OUT / "f1_timeline.png"
    fig.savefig(figs["f1"], dpi=180)
    plt.close(fig)

    # 3) Latence
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    lat = [r["latency_p95_ms"] for r in tl]
    bars = ax.bar(weeks, lat, color=[PALETTE["crit"] if v > p["latency_p95_ms_critical"] else PALETTE["primary"]
                                     for v in lat])
    ax.bar_label(bars, fmt="%.0f", fontsize=7.5, padding=2)
    ax.axhline(p["latency_p95_ms_critical"], ls="--", lw=1, color=PALETTE["crit"])
    ax.set_xticks(weeks)
    ax.set_xlabel("Semaine de production")
    ax.set_ylabel("ms")
    ax.set_title("Opérationnel : latence p95 de l'API (charge simulée)", loc="left", fontsize=11.5,
                 fontweight="bold")
    style_axes(ax)
    fig.tight_layout()
    figs["latency"] = OUT / "latency_timeline.png"
    fig.savefig(figs["latency"], dpi=180)
    plt.close(fig)
    return figs


BADGE = {"OK": "#2A9D8F", "WARNING": "#E9A23B", "CRITICAL": "#C1121F"}
DECISION_FR = {"none": "Aucune action", "watch": "Surveillance renforcée", "investigate": "Analyse humaine",
               "trigger_retraining": "Déclencher le réentraînement (CT)",
               "scale_or_optimize": "Scaler / optimiser l'API"}


def render_dashboard(tl: list[dict], figs: dict[str, Path], title: str) -> Path:
    last = tl[-1]
    rows = "".join(
        f"<tr><td>S{r['week']:02d}</td>"
        + "".join(f"<td><span class='b' style='background:{BADGE[r[k]]}'>{r[k]}</span></td>"
                  for k in ("data_drift", "concept_drift", "operational"))
        + f"<td>{(r['f1_current'] or 0):.3f}</td><td>{max(r['psi'].values()):.3f}</td>"
          f"<td>{r['latency_p95_ms']:.0f} ms</td><td>{DECISION_FR[r['decision']]}</td></tr>"
        for r in tl)
    first_trigger = next((r["week"] for r in tl if r["decision"] == "trigger_retraining"), None)
    html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>
:root{{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;--pri:#0F4C5C}}
body{{margin:0;font-family:Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink)}}
header{{background:var(--pri);color:#fff;padding:22px 32px}}header h1{{margin:0;font-size:22px}}
header p{{margin:6px 0 0;opacity:.85;font-size:13px}}main{{max-width:1180px;margin:0 auto;padding:24px 16px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:20px}}
.k{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.k .l{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}
.k .v{{font-size:26px;font-weight:700;margin-top:4px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}}
.card img{{width:100%;height:auto}}table{{width:100%;border-collapse:collapse;font-size:13px;background:#fff}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}}th{{background:#f1f5f9}}
.b{{color:#fff;border-radius:999px;padding:2px 9px;font-size:11px;font-weight:600}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><header><h1>{title}</h1>
<p>Modèle de prédiction des impayés (default_risk) — data drift, concept drift et santé opérationnelle</p></header>
<main><div class="kpis">
<div class="k"><div class="l">F1-macro (dernière semaine)</div><div class="v">{(last['f1_current'] or 0):.3f}</div></div>
<div class="k"><div class="l">F1 de référence</div><div class="v">{last['f1_reference']:.3f}</div></div>
<div class="k"><div class="l">PSI max</div><div class="v">{max(last['psi'].values()):.2f}</div></div>
<div class="k"><div class="l">Latence p95</div><div class="v">{last['latency_p95_ms']:.0f} ms</div></div>
<div class="k"><div class="l">1er déclenchement CT</div><div class="v">{f'S{first_trigger:02d}' if first_trigger else '—'}</div></div>
</div>
<div class="grid"><div class="card"><img src="{_img(figs['psi'])}" alt="PSI"></div>
<div class="card"><img src="{_img(figs['f1'])}" alt="F1"></div></div>
<div class="card" style="margin-top:16px"><img src="{_img(figs['latency'])}" alt="Latence"></div>
<h2 style="font-size:16px;margin:22px 0 10px">Journal des contrôles hebdomadaires</h2>
<table><tr><th>Semaine</th><th>Data drift</th><th>Concept drift</th><th>Opérationnel</th><th>F1 réel</th>
<th>PSI max</th><th>Latence p95</th><th>Décision</th></tr>{rows}</table>
<p style="color:var(--muted);font-size:12px;margin-top:14px">Seuils : PSI alerte 0,10 / critique 0,25 ; baisse F1
alerte 0,05 / critique 0,10 ; latence p95 critique 300 ms. Un déclenchement CT lance un réentraînement
qui doit encore franchir la quality gate et une validation humaine avant toute mise en production.</p>
</main></body></html>"""
    out = OUT / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


def batch() -> int:
    """Analyse des prédictions loguées par l'API (data/production/predictions.jsonl)."""
    cols = input_columns()
    log_file = path("data/production/predictions.jsonl")
    if not log_file.exists():
        log.warning("Aucune prédiction loguée (%s).", log_file)
        return 0
    cur = pd.read_json(log_file, lines=True)
    ref = pd.read_parquet(path("data/reference/reference.parquet"))
    model = joblib.load(path("models/model.joblib"))
    fb_file = path("data/production/feedback.jsonl")
    y_true = cur_pred = None
    if fb_file.exists():
        fb = pd.read_json(fb_file, lines=True)
        merged = cur.merge(fb, on="request_id", how="inner")
        if len(merged):
            y_true, cur_pred = merged["actual_default_risk"], merged["prediction"]
    f1_ref = json.loads(path("reports/metrics.json").read_text())["f1_macro"]
    rep = analyse(ref[cols], cur[cols], ref_pred=pd.Series(model.predict(ref[cols])),
                  cur_pred=cur_pred if cur_pred is not None else cur["prediction"],
                  f1_reference=f1_ref, y_true=y_true, latency_ms=cur.get("latency_ms", pd.Series()).to_numpy())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest_report.json").write_text(json.dumps(rep.to_dict(), indent=2), encoding="utf-8")
    log.info("Décision : %s | %s", rep.decision, "; ".join(rep.reasons) or "RAS")
    return 3 if rep.decision == "trigger_retraining" else 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["batch", "simulate"])
    a = ap.parse_args()
    if a.mode == "simulate":
        tl = simulate()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "simulation_timeline.json").write_text(json.dumps(tl, indent=2, default=float), encoding="utf-8")
        figs = plot_timeline(tl)
        out = render_dashboard(tl, figs, "Tableau de bord de monitoring — scénario simulé")
        log.info("Tableau de bord : %s", out)
    else:
        sys.exit(batch())


if __name__ == "__main__":
    main()
