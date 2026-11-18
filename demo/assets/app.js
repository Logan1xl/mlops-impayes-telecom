/* ============================================================
   NaijaTel Impayés AI — moteur de démo (100 % hors-ligne)
   Inférence JavaScript du modèle LogReg exporté (model.js)
   ============================================================ */
'use strict';

/* ---------- Utilitaires ---------- */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];
const fmtInt = n => new Intl.NumberFormat('fr-FR').format(Math.round(n));
const fmtNGN = n => fmtInt(n) + ' ₦';
const fmtPct = (x, d = 1) => (100 * x).toFixed(d).replace('.', ',') + ' %';
const dec = (x, n = 2) => x.toFixed(n).replace('.', ',');
const C = 2 * Math.PI * 48; // circonférence du donut

function uid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, ch => {
    const r = (Math.random() * 16) | 0, v = ch === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/* ---------- Onglets ---------- */
$$('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
  $$('.tab-btn').forEach(b => b.setAttribute('aria-selected', String(b === btn)));
  $$('.tab-panel').forEach(p => p.classList.toggle('active', p.id === btn.getAttribute('aria-controls')));
}));

/* ---------- Curseur : remplissage de la piste ---------- */
function paintRange(input) {
  const min = +input.min, max = +input.max, v = +input.value;
  input.style.setProperty('--fill', (((v - min) / (max - min)) * 100).toFixed(1) + '%');
}
$$('input[type=range]').forEach(r => { paintRange(r); r.addEventListener('input', () => paintRange(r)); });

/* ---------- Libellés des variables ---------- */
const FEATURE_FR = {
  tenure_months: 'Ancienneté',
  avg_monthly_spend_ngn: 'Dépense mensuelle',
  recharge_frequency_per_month: 'Recharges / mois',
  payment_consistency_score: 'Régularité des paiements',
  late_payment_count: 'Retards cumulés',
  spend_per_recharge: 'Dépense par recharge',
  late_rate: 'Taux de retard',
  log_spend: 'log(dépense)',
  is_new_customer: 'Nouveau client (< 6 mois)',
  'operator:9mobile': 'Opérateur 9mobile',
  'operator:Airtel': 'Opérateur Airtel',
  'operator:Glo': 'Opérateur Glo',
  'operator:MTN': 'Opérateur MTN',
  'account_type:postpaid': 'Compte postpayé',
  'account_type:prepaid': 'Compte prépayé',
};

/* ---------- Inférence locale (réplique exacte du pipeline sklearn) ---------- */
const MODEL = window.MODEL || { classes: [], numeric: [], scaler_mean: [], scaler_scale: [], ohe_operator: [], ohe_account_type: [], coef: [], intercept: [] };

function engineer(f) {
  const t = Math.max(1, f.tenure_months), r = Math.max(1, f.recharge_frequency_per_month);
  const s = Math.max(0, f.avg_monthly_spend_ngn);
  return [
    f.tenure_months, s, f.recharge_frequency_per_month,
    f.payment_consistency_score, f.late_payment_count,
    s / r, f.late_payment_count / t, Math.log1p(s), f.tenure_months < 6 ? 1 : 0,
  ];
}

function vectorize(f) {
  const eng = engineer(f);
  const scaled = eng.map((v, i) => (v - MODEL.scaler_mean[i]) / MODEL.scaler_scale[i]);
  const oheOp = MODEL.ohe_operator.map(c => (f.operator === c ? 1 : 0));
  const oheAcct = MODEL.ohe_account_type.map(c => (f.account_type === c ? 1 : 0));
  return scaled.concat(oheOp, oheAcct);
}

function softmax(v) {
  const m = Math.max(...v), e = v.map(x => Math.exp(x - m)), s = e.reduce((a, b) => a + b, 0);
  return e.map(x => x / s);
}

function predictLocal(f) {
  const t0 = performance.now();
  const x = vectorize(f);
  const decision = MODEL.coef.map((row, i) => row.reduce((acc, c, j) => acc + c * x[j], MODEL.intercept[i]));
  const proba = softmax(decision);
  const entries = MODEL.classes.map((c, i) => [c, proba[i]]);
  const best = entries.reduce((a, b) => (b[1] > a[1] ? b : a));
  return {
    request_id: uid(), customer_ref: f.customer_ref,
    default_risk: best[0],
    probabilities: Object.fromEntries(entries),
    model_name: 'impayes-default-risk', model_version: MODEL.model_version ?? '1',
    latency_ms: +(performance.now() - t0).toFixed(3),
    mode: 'autonome', x, decision,
  };
}

async function predictRemote(f) {
  const t0 = performance.now();
  const body = {
    tenure_months: f.tenure_months, avg_monthly_spend_ngn: f.avg_monthly_spend_ngn,
    recharge_frequency_per_month: f.recharge_frequency_per_month,
    payment_consistency_score: f.payment_consistency_score,
    late_payment_count: f.late_payment_count,
    operator: f.operator, account_type: f.account_type, customer_ref: f.customer_ref,
  };
  const res = await fetch('http://localhost:8000/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('API HTTP ' + res.status);
  const data = await res.json();
  return { ...data, mode: 'connecté', wall_ms: +(performance.now() - t0).toFixed(1) };
}

function renderError(html) {
  const chip = $('#riskChip');
  chip.textContent = 'Indisponible'; chip.className = 'risk-chip risk-medium';
  $('#donutPct').textContent = '—';
  $('#donutClass').textContent = 'API requise';
  $('#recoText').innerHTML = html;
  $('#factors').innerHTML = '<p class="empty">Mode hors-ligne impossible pour ce modèle.</p>';
  $('#latencyOut').textContent = 'API FastAPI introuvable sur http://localhost:8000';
}

/* ---------- Rendu du résultat ---------- */
const ARC = { low: $('.arc-low'), medium: $('.arc-medium'), high: $('.arc-high') };

function renderResult(r) {
  const p = r.probabilities;
  // Donut : segments cumulés
  let acc = 0;
  for (const cls of ['low', 'medium', 'high']) {
    const frac = p[cls] || 0, arc = ARC[cls];
    arc.style.transition = 'stroke-dasharray .5s ease, stroke-dashoffset .5s ease';
    arc.style.strokeDasharray = `${frac * C} ${C}`;
    arc.style.strokeDashoffset = `${-acc * C}`;
    acc += frac;
  }
  const bestCls = r.default_risk, bestP = p[bestCls];
  $('#donutPct').textContent = fmtPct(bestP, 0);
  $('#donutClass').textContent = bestCls;

  const chip = $('#riskChip');
  chip.textContent = bestCls === 'high' ? 'Risque élevé' : bestCls === 'medium' ? 'Risque moyen' : 'Risque faible';
  chip.className = 'risk-chip risk-' + bestCls;

  $('#recoText').innerHTML = bestCls === 'high'
    ? '<strong>Refuser le crédit</strong> d’appel, ou passer par une validation humaine. Plafond proposé : 0 ₦. Prochaine relance : immédiate, pré-paiement exigé.'
    : bestCls === 'medium'
      ? '<strong>Accorder avec restriction</strong> : plafond réduit de 50 %, recharge test d’abord, surveillance hebdomadaire pendant 60 jours.'
      : '<strong>Accorder le crédit</strong> aux conditions standard. Plafond plein, aucune restriction. Client éligible aux offres fidélité.';

  // Facteurs (contribution linéaire vers la classe gagnante)
  if (r.x) {
    const ci = MODEL.classes.indexOf(bestCls);
    const contrib = r.x.map((v, j) => ({ name: j < 9 ? MODEL.numeric[j] : (j < 13 ? 'operator:' + MODEL.ohe_operator[j - 9] : 'account_type:' + MODEL.ohe_account_type[j - 13]), v: MODEL.coef[ci][j] * v }));
    const top = [...contrib].sort((a, b) => Math.abs(b.v) - Math.abs(a.v)).slice(0, 5)
      .sort((a, b) => Math.abs(a.v) - Math.abs(b.v));
    const maxAbs = Math.max(...top.map(t => Math.abs(t.v)), 1e-9);
    $('#factors').innerHTML = top.map(t => `
      <div class="factor">
        <span class="factor-name">${FEATURE_FR[t.name] || t.name}</span>
        <div class="factor-bar"><div class="factor-fill ${t.v < 0 ? 'neg' : ''}" style="width:${(Math.abs(t.v) / maxAbs * 100).toFixed(1)}%"></div></div>
        <span class="factor-val num">${t.v >= 0 ? '+' : ''}${t.v.toFixed(2)}</span>
      </div>`).join('');
  } else {
    $('#factors').innerHTML = '<p class="empty">Explication détaillée disponible en mode autonome.</p>';
  }

  $('#latencyOut').textContent = r.mode === 'connecté'
    ? `API FastAPI · ${r.latency_ms} ms (réseau ${r.wall_ms} ms)`
    : `inférence locale · ${r.latency_ms < 1 ? '< 1' : r.latency_ms} ms`;

  const curl = `$ curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \\
     -d '{"tenure_months": ${formValues.tenure}, "avg_monthly_spend_ngn": ${formValues.spend}, …}'

→ 200 OK
${JSON.stringify({ request_id: r.request_id, default_risk: r.default_risk,
  probabilities: r.probabilities, model_name: r.model_name, model_version: r.model_version }, null, 2)}`;
  $('#curlBox').textContent = curl;
}

/* ---------- Registre local (localStorage) ---------- */
const REG_KEY = 'impayes_registry_v1';
const loadRegistry = () => { try { return JSON.parse(localStorage.getItem(REG_KEY)) || []; } catch { return []; } };
const saveRegistry = rows => localStorage.setItem(REG_KEY, JSON.stringify(rows.slice(-200)));

function renderRegistry(rows) {
  const count = rows.length;
  $('#registryCount').textContent = `(${count})`;
  $('#registryBody').innerHTML = count
    ? rows.slice().reverse().slice(0, 60).map(r => `
      <tr><td class="num">${r.time}</td><td class="mono">${String(r.ref).slice(0, 13)}…</td>
        <td><span class="badge-mini ${r.risk}">${r.risk}</span></td>
        <td class="num">${fmtPct(r.pHigh, 1)}</td><td>${r.mode}</td></tr>`).join('')
    : '<tr><td colspan="5" class="empty">Aucune décision enregistrée.</td></tr>';
}

function addToRegistry(r) {
  const rows = loadRegistry();
  rows.push({ time: new Date().toLocaleTimeString('fr-FR'), ref: r.customer_ref || '—',
    risk: r.default_risk, pHigh: r.probabilities.high ?? 0, mode: r.mode === 'connecté' ? 'API' : 'local' });
  saveRegistry(rows);
  renderRegistry(rows);
}

$('#exportCsv').addEventListener('click', () => {
  const rows = loadRegistry();
  const csv = ['heure;ref;risque;proba_high;mode',
    ...rows.map(r => [r.time, r.ref, r.risk, (r.pHigh * 100).toFixed(2) + '%', r.mode].join(';'))].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  a.download = 'registre_decisions.csv';
  a.click();
  URL.revokeObjectURL(a.href);
});
$('#clearRegistry').addEventListener('click', () => { localStorage.removeItem(REG_KEY); renderRegistry([]); });

/* ---------- Formulaire ---------- */
const formValues = { tenure: 7, spend: 48856 };
function readForm() {
  return {
    customer_ref: $('#customer_ref').value,
    tenure_months: +$('#tenure').value,
    avg_monthly_spend_ngn: +$('#spend').value,
    recharge_frequency_per_month: +$('#recharge').value,
    payment_consistency_score: +$('#consistency').value,
    late_payment_count: +$('#late').value,
    operator: $('#operator').value,
    account_type: ($('input[name=account_type]:checked') || {}).value || 'prepaid',
  };
}
function syncOutputs() {
  $('#out_tenure').textContent = $('#tenure').value + ' mois';
  $('#out_spend').textContent = fmtNGN(+$('#spend').value);
  $('#out_recharge').textContent = $('#recharge').value;
  $('#out_consistency').textContent = dec(+$('#consistency').value, 2);
  $('#out_late').textContent = $('#late').value;
  formValues.tenure = +$('#tenure').value; formValues.spend = +$('#spend').value;
}
['tenure', 'spend', 'recharge', 'consistency', 'late'].forEach(id =>
  $('#' + id).addEventListener('input', syncOutputs));

const PRESETS = {
  loyal: { tenure: 48, spend: 38034, recharge: 19, consistency: 0.85, late: 1, operator: 'MTN', account_type: 'prepaid' },
  new:   { tenure: 3,  spend: 15500, recharge: 8,  consistency: 0.50, late: 2, operator: 'Glo', account_type: 'prepaid' },
  late:  { tenure: 14, spend: 22000, recharge: 6,  consistency: 0.25, late: 17, operator: '9mobile', account_type: 'prepaid' },
  risk:  { tenure: 6,  spend: 48856, recharge: 5,  consistency: 0.05, late: 24, operator: 'Airtel', account_type: 'postpaid' },
};
$$('.preset').forEach(btn => btn.addEventListener('click', () => {
  const p = PRESETS[btn.dataset.preset]; if (!p) return;
  $('#tenure').value = p.tenure; $('#spend').value = p.spend; $('#recharge').value = p.recharge;
  $('#consistency').value = p.consistency; $('#late').value = p.late; $('#operator').value = p.operator;
  $('input[name=account_type][value="' + p.account_type + '"]').checked = true;
  $$('input[type=range]').forEach(paintRange);
  syncOutputs();
}));

$('#regenRef').addEventListener('click', () => { $('#customer_ref').value = 'CLI-' + uid().slice(0, 8).toUpperCase(); });

/* ---------- Mode (autonome / connecté) ---------- */
let apiOnline = false;
const modeToggle = $('#modeToggle');
function setModeLabel() {
  const remote = modeToggle.checked;
  $('#modeLabel').textContent = MODEL.unsupported
    ? 'Mode connecté — requis par le modèle (' + (MODEL.model_class || 'non-LogReg') + ')'
    : (remote ? 'Mode connecté (API FastAPI)' : 'Mode autonome (navigateur)');
}
modeToggle.addEventListener('change', setModeLabel);

(async function detectApi() {
  const badge = $('#connBadge');
  // Modèle non-LogReg ré-entraîné : le mode connecté est obligatoire
  if (MODEL.unsupported) {
    modeToggle.checked = true; modeToggle.disabled = true;
    setModeLabel();
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 1500);
      const res = await fetch('http://localhost:8000/health', { signal: ctrl.signal, cache: 'no-store' });
      clearTimeout(timer);
      if (res.ok) { apiOnline = true; badge.innerHTML = '<span class="dot"></span>API requise — connectée'; }
      else throw new Error();
    } catch {
      apiOnline = false;
      badge.innerHTML = '<span class="dot"></span>API requise — hors ligne';
      badge.classList.add('offline');
    }
    return;
  }
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch('http://localhost:8000/health', { signal: ctrl.signal, cache: 'no-store' });
    clearTimeout(timer);
    if (res.ok) {
      apiOnline = true;
      badge.innerHTML = '<span class="dot"></span>API connectée';
      badge.classList.remove('offline');
      badge.title = 'API FastAPI joignable sur http://localhost:8000';
      modeToggle.checked = true;
      setModeLabel();
      return;
    }
    throw new Error('HTTP ' + res.status);
  } catch {
    apiOnline = false;
    badge.innerHTML = '<span class="dot"></span>Mode autonome';
    badge.classList.add('offline');
    badge.title = 'API non détectée — inférence locale active (aucune installation requise)';
  }
})();

async function runPrediction({ record = true } = {}) {
  const f = readForm();
  if (!f.customer_ref) f.customer_ref = 'CLI-' + uid().slice(0, 8).toUpperCase();
  $('#customer_ref').value = f.customer_ref;
  const btn = $('#predictBtn');
  btn.disabled = true; btn.textContent = 'Évaluation…';
  try {
    let r;
    if (MODEL.unsupported) {
      // Modèle non-LogReg ré-entraîné : inférence exclusivement via l'API
      try { r = await predictRemote(f); }
      catch {
        renderError('Le modèle actuellement publié (<code>' + (MODEL.model_class || 'non-LogReg') + '</code>) ne peut pas tourner dans le navigateur.<br>Démarrez l’API puis réessayez :<br><code class="mono">uvicorn impayes.api.main:app --port 8000</code>');
        return;
      }
    } else if (modeToggle.checked && apiOnline) {
      try { r = await predictRemote(f); }
      catch (err) {
        console.warn('API indisponible, repli autonome :', err);
        r = predictLocal(f);
        r.mode = 'autonome (repli)';
      }
    } else {
      r = predictLocal(f);
    }
    renderResult(r);
    if (record) addToRegistry(r);
  } finally {
    btn.disabled = false; btn.innerHTML = '⚡ Évaluer le risque';
  }
}

$('#scoreForm').addEventListener('submit', e => { e.preventDefault(); runPrediction({ record: true }); });

/* ============================================================
   ONGLET ARGUMENTAIRE — calculateur ROI
   ============================================================ */
const roi = { clients: $('#roi_clients'), spend: $('#roi_spend'), rate: $('#roi_rate'), reduction: $('#roi_reduction') };
function computeROI() {
  const clients = +roi.clients.value, spend = +roi.spend.value, rate = +roi.rate.value / 100, reduction = +roi.reduction.value / 100;
  const before = clients * spend * rate * 12;
  const after = before * (1 - reduction);
  const save = before - after;
  $('#roi_clients_out').textContent = fmtInt(clients);
  $('#roi_spend_out').textContent = fmtNGN(spend);
  $('#roi_rate_out').textContent = dec(+roi.rate.value, 1) + ' %';
  $('#roi_reduction_out').textContent = dec(+roi.reduction.value, 0) + ' %';
  $('#roiResult').textContent = fmtNGN(save);
  $('#roiDetail').textContent = `Pertes actuelles ≈ ${fmtNGN(before)} / an → après IA ≈ ${fmtNGN(after)} (réduction de ${dec(reduction * 100, 0)} %).`;
}
Object.values(roi).forEach(el => el.addEventListener('input', computeROI));

$$('.price-card [data-offer]').forEach(btn => btn.addEventListener('click', () => {
  const offer = btn.dataset.offer;
  window.location.href = 'mailto:contact@naijatel.example?subject=' +
    encodeURIComponent(`[Impayés AI] Demande — offre ${offer}`) +
    '&body=' + encodeURIComponent(`Bonjour,\n\nJe souhaite l'offre « ${offer} » pour Impayés AI (démo du CC1).\n\nContexte : `);
}));

/* ============================================================
   ONGLET PERFORMANCE
   ============================================================ */
const METRICS = window.METRICS || {};
(function renderPerformance() {
  const comp = (METRICS.comparison || []).slice().sort((a, b) => b.f1_macro - a.f1_macro);
  const maxF1 = Math.max(...comp.map(c => c.f1_macro), 0.01);
  $('#candidateBars').innerHTML = comp.map(c => `
    <div class="bar-row">
      <span>${({ logreg: 'Régression logistique', random_forest: 'Random Forest', hist_gbm: 'HistGradientBoosting' })[c.model] || c.model}${c.model === 'logreg' ? ' ✓' : ''}</span>
      <div class="bar-track"><div class="bar-fill ${c.model === 'logreg' ? 'winner' : ''}" style="width:${(c.f1_macro / maxF1 * 100).toFixed(1)}%"></div></div>
      <span class="bar-val num">${c.f1_macro.toFixed(3)}</span>
    </div>`).join('');

  const cm = METRICS.test?.confusion_matrix;
  if (cm) {
    const labels = cm.labels, matrix = cm.matrix;
    const rowMax = matrix.map(r => Math.max(...r));
    $('#cmBody').innerHTML = matrix.map((row, i) => `
      <tr><th class="row-label" scope="row">${labels[i]}</th>${row.map((v, j) => {
        const alpha = (v / (rowMax[i] || 1)).toFixed(2);
        const good = i === j;
        return `<td style="background:rgba(${good ? '13,148,136' : '244,63,94'},${(0.08 + 0.55 * (v / (rowMax[i] || 1))).toFixed(2)})">${fmtInt(v)}<br><small style="font-weight:400;color:var(--muted)">${fmtPct(v / row.reduce((a, b) => a + b, 0), 0)}</small></td>`;
      }).join('')}</tr>`).join('');
  }

  const gate = METRICS.test?.quality_gate;
  if (gate) {
    const names = { 'f1_macro >= min': 'F1-macro ≥ 0,45 (seuil qualité)', 'recall_high >= min': 'Rappel « high » ≥ 0,60', 'latency_p95 <= max': 'Latence p95 ≤ 150 ms', 'no_regression_vs_production': 'Non-régression vs production (tolérance 0,01)' };
    $('#gateList').innerHTML = Object.entries(gate.checks).map(([k, ok]) => `
      <li><span class="gate-ok">${ok ? '✓' : '✗'}</span> ${names[k] || k} <span style="margin-left:auto" class="${ok ? 'gate-ok' : ''}">${ok ? 'PASS' : 'ÉCHEC'}</span></li>`).join('');
  }

  const imp = METRICS.test?.permutation_importance;
  if (imp) {
    const entries = Object.entries(imp).sort((a, b) => b[1] - a[1]).slice(0, 6);
    const maxImp = Math.max(...entries.map(([, v]) => v), 1e-9);
    $('#importanceBars').innerHTML = entries.map(([k, v]) => `
      <div class="bar-row"><span>${FEATURE_FR[k] || k}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${(v / maxImp * 100).toFixed(1)}%"></div></div>
        <span class="bar-val num">${v.toFixed(3)}</span>
      </div>`).join('');
  }
})();

/* ============================================================
   ONGLET TRAÇABILITÉ — export MLflow
   ============================================================ */
const TRACE = window.TRACE || { runs: [], audit: [] };
(function renderTrace() {
  const fmtDate = ms => ms ? new Date(ms).toLocaleString('fr-FR') : '—';
  $('#runsBody').innerHTML = (TRACE.runs || []).map(r => `
    <tr style="${r.selected ? 'background:#f0fdf9' : ''}">
      <td class="mono">${r.run_id.slice(0, 8)}${r.selected ? ' <span class="badge-mini low">retenu</span>' : ''}</td>
      <td>${r.model || '—'}</td>
      <td class="num">${(r.metrics?.val_f1_macro ?? 0).toFixed(3)}</td>
      <td class="num">${(r.metrics?.val_auc_ovr_macro ?? 0).toFixed(3)}</td>
      <td class="num">${r.metrics?.test_f1_macro ? r.metrics.test_f1_macro.toFixed(3) : '—'}</td>
      <td><span class="tag">git ${String(r.git_commit || '∅').slice(0, 7)}</span><span class="tag">dvc ${String(r.data_version || '∅').slice(0, 8)}</span></td>
    </tr>`).join('');

  $('#auditBody').innerHTML = (TRACE.audit || []).map(a => `
    <tr><td class="num">${new Date(a.ts).toLocaleString('fr-FR')}</td>
      <td>${a.action} → <strong>${a.to || a.alias || ''}</strong></td>
      <td class="mono">v${a.version || ''} ${a.reason ? '· ' + a.reason : ''}</td>
      <td>${a.approved_by || '—'}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">Aucun événement.</td></tr>';
})();

/* ---------- Initialisation ---------- */
$('#customer_ref').value = 'CLI-' + uid().slice(0, 8).toUpperCase();
syncOutputs();
computeROI();
renderRegistry(loadRegistry());
// Évalue le profil affiché au chargement (démo immédiate en présentation) — sans journaliser
runPrediction({ record: false });
