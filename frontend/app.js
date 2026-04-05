/**
 * AegisClaim AI — Frontend Application v2.0
 * Classic premium UI with full OCR display, citation indexing, and rich result panels.
 */

'use strict';

// ── Config ──────────────────────────────────────────────────────────────────
const API_BASE = '/api/v1';

// ── State ───────────────────────────────────────────────────────────────────
let billFile = null;
let policyFile = null;
let currentResult = null;
let currentClaimId = null;
const sessionHistory = [];

// ── Element refs ─────────────────────────────────────────────────────────────
const billInput       = document.getElementById('bill-input');
const policyInput     = document.getElementById('policy-input');
const billZone        = document.getElementById('bill-upload-zone');
const policyZone      = document.getElementById('policy-upload-zone');
const billFileName    = document.getElementById('bill-file-name');
const policyFileName  = document.getElementById('policy-file-name');
const btnProcess      = document.getElementById('btn-process');
const btnOcrOnly      = document.getElementById('btn-ocr-only');
const ocrLang         = document.getElementById('ocr-language');

const uploadSection     = document.getElementById('upload-section');
const processingSection = document.getElementById('processing-section');
const resultsSection    = document.getElementById('results-section');
const historySection    = document.getElementById('history-section');
const evalSection       = document.getElementById('evaluation-section');
const analyticsSection  = document.getElementById('analytics-section');

const decidedBanner   = document.getElementById('decision-banner');
const decisionBadge   = document.getElementById('decision-badge');
const claimIdEl       = document.getElementById('claim-id');
const procTimeEl      = document.getElementById('proc-time');
const modelUsedEl     = document.getElementById('model-used');
const confidenceVal   = document.getElementById('confidence-value');
const confidenceFill  = document.getElementById('confidence-fill');
const billAmountEl    = document.getElementById('bill-amount');
const approvedAmountEl= document.getElementById('approved-amount');
const fraudScoreEl    = document.getElementById('fraud-score');
const fraudCardEl     = document.getElementById('fraud-card');

// ── Utility: Format currency ─────────────────────────────────────────────────
function fmt(n, currency = '₹') {
  if (n == null || isNaN(n)) return '—';
  return `${currency}${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPct(n) {
  if (n == null || isNaN(n)) return '—';
  // API returns confidence as 0.0-1.0; multiply by 100 if needed
  const val = Number(n);
  return `${(val <= 1.0 && val >= 0 ? val * 100 : val).toFixed(1)}%`;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Upload Zones ─────────────────────────────────────────────────────────────
function setupDropZone(zone, input, fileNameEl, onFile) {
  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    if (input.files[0]) handleFile(input.files[0]);
  });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });

  function handleFile(file) {
    onFile(file);
    zone.classList.add('has-file');
    fileNameEl.textContent = `✓ ${file.name}`;
    checkReady();
  }
}

setupDropZone(billZone, billInput, billFileName, f => billFile = f);
setupDropZone(policyZone, policyInput, policyFileName, f => policyFile = f);

function checkReady() {
  const billReady = !!billFile;
  const bothReady = billFile && policyFile;
  btnOcrOnly.disabled = !billReady;
  btnProcess.disabled = !bothReady;
}

// ── Nav Buttons ──────────────────────────────────────────────────────────────
const btnEval      = document.getElementById('btn-eval');
const btnAnalytics = document.getElementById('btn-analytics');
const btnHistory   = document.getElementById('btn-history');

function hideAllSections() {
  uploadSection.classList.remove('hidden');
  processingSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  historySection.classList.add('hidden');
  evalSection.classList.add('hidden');
  analyticsSection.classList.add('hidden');
}

function setActiveNav(btn) {
  [btnEval, btnAnalytics, btnHistory].forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

btnEval.addEventListener('click', () => {
  setActiveNav(btnEval);
  hideAllSections();
  if (currentResult) resultsSection.classList.remove('hidden');
});

btnHistory.addEventListener('click', () => {
  setActiveNav(btnHistory);
  uploadSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  analyticsSection.classList.add('hidden');
  evalSection.classList.add('hidden');
  historySection.classList.remove('hidden');
  renderHistory();
});

btnAnalytics.addEventListener('click', () => {
  setActiveNav(btnAnalytics);
  uploadSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  historySection.classList.add('hidden');
  evalSection.classList.add('hidden');
  analyticsSection.classList.remove('hidden');
  loadAnalytics();
});

// ── Logo click → back to Evaluate ───────────────────────────────────────────
document.querySelector('.logo-section').addEventListener('click', () => {
  setActiveNav(btnEval);
  hideAllSections();
  if (currentResult) resultsSection.classList.remove('hidden');
});

// ── Processing Step Tracker ──────────────────────────────────────────────────
const STEPS = ['step-ocr', 'step-rag', 'step-decision', 'step-explain', 'step-fraud'];

function setStep(index, label) {
  document.getElementById('processing-step').textContent = label;
  STEPS.forEach((id, i) => {
    const el = document.getElementById(id);
    el.classList.remove('active', 'done');
    if (i < index) el.classList.add('done');
    else if (i === index) el.classList.add('active');
  });
}

function showProcessing() {
  uploadSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  processingSection.classList.remove('hidden');
  setStep(0, 'Running OCR Extraction…');
}

function showResults() {
  processingSection.classList.add('hidden');
  uploadSection.classList.remove('hidden');
  resultsSection.classList.remove('hidden');
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
document.querySelectorAll('.rtab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.rtab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.rpanel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    const panelId = `panel-${tab.dataset.tab}`;
    document.getElementById(panelId)?.classList.add('active');
  });
});

// ── OCR Only ─────────────────────────────────────────────────────────────────
btnOcrOnly.addEventListener('click', async () => {
  if (!billFile) return;
  showProcessing();
  setStep(0, 'Extracting bill data via OCR…');
  try {
    const fd = new FormData();
    fd.append('bill', billFile);
    if (ocrLang.value) fd.append('language', ocrLang.value);
    const resp = await fetch(`${API_BASE}/claims/ocr`, { method: 'POST', body: fd });
    if (!resp.ok) throw new Error((await resp.json()).detail || 'OCR failed');
    const data = await resp.json();
    processingSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    // Render OCR-only result in extracted tab
    renderExtractedData(data, null);
    resultsSection.classList.remove('hidden');
    // Activate extracted tab
    document.querySelector('[data-tab="extracted"]').click();
    // Hide verdict (no full decision yet)
    decidedBanner.style.display = 'none';
  } catch (e) {
    processingSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    alert(`OCR Error: ${e.message}`);
  }
});

// ── Main Process Claim ────────────────────────────────────────────────────────
btnProcess.addEventListener('click', async () => {
  if (!billFile || !policyFile) return;

  showProcessing();
  decidedBanner.style.display = '';

  const fd = new FormData();
  fd.append('bill', billFile);
  fd.append('policy', policyFile);
  if (ocrLang.value) fd.append('language', ocrLang.value);

  // Simulate pipeline steps while waiting
  const stepMessages = [
    [0, 'Running OCR on Hospital Bill…'],
    [1, 'Indexing Policy & Running RAG…'],
    [2, 'Hybrid Decision Engine Processing…'],
    [3, 'Generating Explainability Report…'],
    [4, 'Running Fraud Analysis…'],
  ];
  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    if (stepIdx < stepMessages.length) {
      const [i, msg] = stepMessages[stepIdx];
      setStep(i, msg);
      stepIdx++;
    }
  }, 2200);

  try {
    const resp = await fetch(`${API_BASE}/claims/process`, { method: 'POST', body: fd });
    clearInterval(stepInterval);
    setStep(4, 'Finalizing…');

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || 'Processing failed');
    }

    const data = await resp.json();
    currentResult = data;
    currentClaimId = data.claim_id;

    // Add to session history
    sessionHistory.unshift({
      claim_id: data.claim_id,
      decision: data.explanation?.decision || 'ERROR',
      amount: data.explanation?.total_bill_amount || 0,
      approved: data.explanation?.total_approved_amount || 0,
      time: new Date().toLocaleTimeString(),
      bill_name: billFile.name,
    });
    updateDashboardCounter();

    await new Promise(r => setTimeout(r, 400));
    showResults();
    renderFullResult(data);

  } catch (e) {
    clearInterval(stepInterval);
    processingSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    alert(`Error: ${e.message}`);
  }
});

// ── Dashboard counter ─────────────────────────────────────────────────────────
function updateDashboardCounter() {
  document.getElementById('dash-processed').textContent = sessionHistory.length;
}

// ─────────────────────────────────────────────────────────────────────────────
//  RENDER FULL RESULT
// ─────────────────────────────────────────────────────────────────────────────
function renderFullResult(data) {
  renderVerdict(data);
  renderExtractedData(data.ocr_result, data.explanation);
  renderExplanation(data.explanation);
  renderCitations(data.explanation);
  renderItemAnalysis(data.explanation);
  renderSimulation(data.simulation);
  renderFraud(data.fraud_analysis);
  document.getElementById('raw-json-content').textContent = JSON.stringify(data, null, 2);

  // Default to extracted tab
  document.querySelector('[data-tab="extracted"]').click();
}

// ── Verdict Banner ────────────────────────────────────────────────────────────
function renderVerdict(data) {
  const exp = data.explanation;
  if (!exp) return;

  const decision = exp.decision || 'NEEDS_REVIEW';
  const decisionClass = decision.toLowerCase().replace(/_/g, '-');

  decisionBadge.textContent = decision.replace(/_/g, ' ');
  decisionBadge.className = `verdict-badge ${decisionClass}`;
  claimIdEl.textContent = `Claim ID: ${data.claim_id || '—'}`;
  procTimeEl.textContent = `Processing: ${data.processing_time_ms ? data.processing_time_ms.toFixed(0) + ' ms' : '—'}`;
  modelUsedEl.textContent = `Model: Gemini (Flash)`;

  const conf = exp.confidence || 0;
  const confPct = conf <= 1.0 ? conf * 100 : conf;  // normalize 0-1 → 0-100
  confidenceVal.textContent = fmtPct(conf);
  confidenceFill.style.width = `${Math.min(confPct, 100)}%`;

  billAmountEl.textContent = fmt(exp.total_bill_amount);
  approvedAmountEl.textContent = fmt(exp.total_approved_amount);

  if (data.fraud_analysis) {
    const fr = data.fraud_analysis;
    fraudScoreEl.textContent = `${fr.fraud_risk_score?.toFixed(0) || '0'}%`;
    const lvl = (fr.risk_level || 'LOW').toLowerCase();
    fraudScoreEl.className = `vmetric-value ${lvl}`;
  }
}

// ── Extracted Data ────────────────────────────────────────────────────────────
function renderExtractedData(ocrResult, explanation) {
  const bill = ocrResult?.bill_data || ocrResult;
  if (!bill) return;

  // Patient info
  const patientFields = [
    ['Patient Name',   bill.patient_name],
    ['Patient ID',     bill.patient_id],
    ['Age',            bill.patient_age ? `${bill.patient_age} yrs` : null],
    ['Hospital',       bill.hospital_name],
    ['Diagnosis',      bill.diagnosis],
    ['Doctor',         bill.treating_doctor],
    ['Admission',      bill.admission_date],
    ['Discharge',      bill.discharge_date],
    ['Bill No.',       bill.bill_number],
    ['Bill Date',      bill.bill_date],
  ];
  document.getElementById('patient-details').innerHTML = patientFields
    .filter(([, v]) => v)
    .map(([k, v]) => `
      <div class="field-row">
        <span class="field-key">${escHtml(k)}</span>
        <span class="field-val">${escHtml(v)}</span>
      </div>`)
    .join('') || '<div class="field-row"><span class="field-key">No data extracted</span></div>';

  // Policy info block
  const policyMeta = explanation?.cited_clauses?.length
    ? [
        ['Decision',      explanation.decision],
        ['Confidence',    fmtPct(explanation.confidence)],
        ['Bill Amount',   fmt(explanation.total_bill_amount)],
        ['Approved',      fmt(explanation.total_approved_amount)],
        ['Clauses Cited', explanation.cited_clauses.length],
        ['Language',      bill.language_detected || '—'],
      ]
    : [
        ['Language',      bill.language_detected || 'auto'],
        ['OCR Confidence', fmtPct(bill.extraction_confidence || 0)],
        ['Currency',      bill.currency || 'INR'],
        ['Pages',         ocrResult?.pages_processed || 1],
        ['OCR Engine',    ocrResult?.ocr_engine || 'tesseract'],
      ];

  document.getElementById('policy-details').innerHTML = policyMeta
    .map(([k, v]) => `
      <div class="field-row">
        <span class="field-key">${escHtml(k)}</span>
        <span class="field-val">${escHtml(String(v || '—'))}</span>
      </div>`)
    .join('');

  // OCR Raw text block
  const rawText = bill.raw_text || '(no raw text captured)';
  const ocrConf = (bill.extraction_confidence || 0) * 100;
  document.getElementById('ocr-confidence-badge').textContent = `OCR Confidence: ${ocrConf.toFixed(0)}%`;
  document.getElementById('ocr-confidence-badge').style.background = ocrConf >= 70 ? '#d1fae5' : ocrConf >= 40 ? '#fef3c7' : '#fee2e2';
  document.getElementById('ocr-confidence-badge').style.color = ocrConf >= 70 ? '#065f46' : ocrConf >= 40 ? '#92400e' : '#991b1b';

  // Warnings
  const warnings = bill.warnings || [];
  const warnEl = document.getElementById('ocr-warnings');
  warnEl.innerHTML = warnings.map(w => `
    <div class="ocr-warning-item">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      ${escHtml(w)}
    </div>`).join('');

  // Truncate raw text for display (keep page markers visible)
  const displayText = rawText.length > 2000 ? rawText.slice(0, 2000) + '\n\n… [truncated for display]' : rawText;
  document.getElementById('ocr-raw-text').textContent = displayText;

  // Bill line items table
  const items = bill.line_items || [];
  const tbody = document.getElementById('bill-items-body');
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:20px;">No line items extracted from bill</td></tr>';
  } else {
    tbody.innerHTML = items.map((item, i) => `
      <tr>
        <td style="color:var(--text-muted); font-family:var(--font-mono); font-size:0.75rem;">${i + 1}</td>
        <td style="font-weight:600; color:var(--text-primary);">${escHtml(item.description || '—')}</td>
        <td><span class="cat-badge">${escHtml((item.category || 'unknown').replace(/_/g, ' '))}</span></td>
        <td style="font-family:var(--font-mono); text-align:center;">${item.quantity || 1}</td>
        <td style="font-family:var(--font-mono); font-weight:700; text-align:right;">${fmt(item.amount)}</td>
      </tr>`).join('');

    // Total row
    const total = bill.total_amount || items.reduce((s, i) => s + (i.amount || 0), 0);
    tbody.innerHTML += `
      <tr class="total-row">
        <td colspan="4" style="text-align:right; font-weight:700;">TOTAL</td>
        <td style="font-family:var(--font-mono); font-weight:800; text-align:right; color:var(--navy-700);">${fmt(total)}</td>
      </tr>`;
  }
}

// ── Explanation Tab ───────────────────────────────────────────────────────────
function renderExplanation(exp) {
  if (!exp) {
    document.getElementById('explanation-content').innerHTML = '<p class="muted-text">No explanation available.</p>';
    return;
  }

  const decision = exp.decision || 'NEEDS_REVIEW';
  const decisionColors = {
    APPROVED:           { bg: '#d1fae5', border: '#10b981', text: '#065f46' },
    REJECTED:           { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' },
    PARTIALLY_APPROVED: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
    NEEDS_REVIEW:       { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
  };
  const dc = decisionColors[decision] || decisionColors.NEEDS_REVIEW;

  let html = `
    <div style="background:${dc.bg}; border:1.5px solid ${dc.border}; border-radius:12px; padding:20px 24px; margin-bottom:24px;">
      <div style="font-family:var(--font-serif); font-size:1.4rem; font-weight:700; color:${dc.text}; margin-bottom:8px;">
        ${decision.replace(/_/g, ' ')}
      </div>
      <div style="font-size:0.85rem; color:${dc.text}; opacity:0.85; display:flex; gap:20px; flex-wrap:wrap;">
        <span><strong>Confidence:</strong> ${fmtPct(exp.confidence)}</span>
        <span><strong>Bill:</strong> ${fmt(exp.total_bill_amount)}</span>
        <span><strong>Approved:</strong> ${fmt(exp.total_approved_amount)}</span>
        ${exp.total_bill_amount > 0 ? `<span><strong>Coverage:</strong> ${fmtPct(exp.total_approved_amount / exp.total_bill_amount)}</span>` : ''}
      </div>
    </div>`;

  // Overall reasoning (markdown-ish → HTML)
  if (exp.overall_reasoning) {
    html += `<div class="explanation-prose">` + markdownToHtml(exp.overall_reasoning) + `</div>`;
  }

  // Decision factors
  if (exp.decision_factors?.length) {
    html += `<h3 style="font-family:var(--font-serif); font-size:1rem; color:var(--text-primary); margin:20px 0 10px;">Decision Factors</h3>
    <ul style="padding-left:18px; margin:0 0 16px;">
      ${exp.decision_factors.map(f => `<li style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:6px;">${escHtml(f)}</li>`).join('')}
    </ul>`;
  }

  // Review notice
  if (exp.requires_human_review && exp.review_reasons?.length) {
    html += `
      <div style="background:#fef3c7; border:1.5px solid #f59e0b; border-radius:10px; padding:16px 20px; margin-top:20px;">
        <div style="font-weight:700; color:#92400e; margin-bottom:8px; font-family:var(--font-serif);">⚠ Human Review Required</div>
        <ul style="padding-left:16px; margin:0;">
          ${exp.review_reasons.map(r => `<li style="font-size:0.83rem; color:#92400e; margin-bottom:4px;">${escHtml(r)}</li>`).join('')}
        </ul>
      </div>`;
  }

  document.getElementById('explanation-content').innerHTML = html;

  // Recommendations
  const recsEl = document.getElementById('recommendations');
  if (exp.recommendations?.length) {
    recsEl.innerHTML = `
      <h4>Recommendations</h4>
      <ul>${exp.recommendations.map(r => `<li>${escHtml(r)}</li>`).join('')}</ul>`;
    recsEl.classList.remove('hidden');
  } else {
    recsEl.innerHTML = '';
  }
}

function markdownToHtml(text) {
  if (!text) return '';
  return text
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/^(?!<[hup]|<\/)/gm, '')
    .replace(/\n/g, '<br>');
}

// ── Citations Tab ─────────────────────────────────────────────────────────────
function renderCitations(exp) {
  const container = document.getElementById('citations-list');
  if (!exp) { container.innerHTML = '<div class="no-citations">No explanation available.</div>'; return; }

  // Gather all item-level citations
  const itemCitations = (exp.item_explanations || [])
    .filter(item => item.status !== 'COVERED' || item.clause_text)
    .map(item => ({
      type: 'item',
      bill_item: item.bill_item,
      amount: item.amount,
      approved_amount: item.approved_amount,
      status: item.status,
      clause_text: item.clause_text || item.reasoning || '',
      clause_section: item.clause_section || '',
      page_number: item.page_number,
      reasoning: item.reasoning,
      policy_reference: item.policy_reference || '',
    }));

  // Also gather top-level cited clauses
  const topLevelClauses = (exp.cited_clauses || [])
    .filter(c => c.clause_text || c.text)
    .map(c => ({
      type: 'clause',
      clause_text: c.clause_text || c.text || '',
      page_number: c.page || c.page_number,
      paragraph: c.paragraph,
      clause_section: c.section || c.clause_section || '',
      relevance: c.relevance || 'Referenced during evaluation',
    }));

  if (!itemCitations.length && !topLevelClauses.length) {
    container.innerHTML = '<div class="no-citations">No policy clauses were cited for this claim.</div>';
    return;
  }

  let html = '';

  // Item-level citations first
  if (itemCitations.length) {
    html += `<div style="font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-muted); margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border);">Item-Level Policy Citations (${itemCitations.length})</div>`;

    itemCitations.forEach((item, idx) => {
      const statusClass = {
        'NOT_COVERED':        'rejected',
        'PARTIALLY_COVERED':  'partial',
        'COVERED':            'approved',
        'NEEDS_REVIEW':       'partial',
      }[item.status] || 'rejected';

      const pageStr = item.page_number ? `Pg. ${item.page_number}` : null;
      // Parse paragraph from policy_reference if present
      const paraMatch = (item.policy_reference || '').match(/[Pp]ara(?:graph)?\s*(\d+)/);
      const paraStr = paraMatch ? `¶ ${paraMatch[1]}` : null;
      const sectionStr = item.clause_section || null;

      html += `
        <div class="citation-card ${statusClass}-cite">
          <div class="citation-header">
            <div class="citation-ref-group">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              ${pageStr ? `<span class="cite-page-badge"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16"/><rect x="6" y="6" width="12" height="16" rx="1"/></svg> ${escHtml(pageStr)}</span>` : ''}
              ${paraStr ? `<span class="cite-para-badge">⁋ ${escHtml(paraStr)}</span>` : ''}
              ${sectionStr ? `<span class="cite-section-name">${escHtml(sectionStr.replace(/_/g, ' '))}</span>` : ''}
            </div>
            <span class="cite-decision-chip ${statusClass}">${escHtml(item.status.replace(/_/g, ' '))}</span>
          </div>
          <div class="citation-body">
            <div class="citation-item-name">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 7H6a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-3"/><path d="M9 15h3l8.5-8.5a1.5 1.5 0 0 0-3-3L9 12v3"/></svg>
              ${escHtml(item.bill_item)} — ${fmt(item.amount)}
              ${item.approved_amount < item.amount ? `<span style="font-size:0.75rem; color:var(--approved); font-weight:500;">(Approved: ${fmt(item.approved_amount)})</span>` : ''}
            </div>
            ${item.clause_text ? `
              <div class="citation-clause-text">
                <div class="citation-clause-inner">${escHtml(item.clause_text.slice(0, 500))}${item.clause_text.length > 500 ? '…' : ''}</div>
              </div>` : ''}
            ${item.reasoning ? `
              <div class="citation-reasoning">
                <strong>AI Reasoning:</strong> ${escHtml(item.reasoning)}
              </div>` : ''}
          </div>
        </div>`;
    });
  }

  // Top-level clauses
  if (topLevelClauses.length) {
    html += `<div style="font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-muted); margin:20px 0 12px; padding-bottom:8px; border-bottom:1px solid var(--border);">Referenced Policy Clauses (${topLevelClauses.length})</div>`;

    topLevelClauses.forEach(clause => {
      const pageStr = clause.page_number ? `Pg. ${clause.page_number}` : null;
      const paraStr = clause.paragraph ? `¶ ${clause.paragraph}` : null;

      html += `
        <div class="citation-card">
          <div class="citation-header">
            <div class="citation-ref-group">
              ${pageStr ? `<span class="cite-page-badge">${escHtml(pageStr)}</span>` : '<span class="cite-page-badge">—</span>'}
              ${paraStr ? `<span class="cite-para-badge">${escHtml(paraStr)}</span>` : ''}
              ${clause.clause_section ? `<span class="cite-section-name">${escHtml(clause.clause_section.replace(/_/g, ' '))}</span>` : ''}
            </div>
          </div>
          <div class="citation-body">
            ${clause.clause_text ? `
              <div class="citation-clause-text">
                <div class="citation-clause-inner">${escHtml(clause.clause_text.slice(0, 500))}${clause.clause_text.length > 500 ? '…' : ''}</div>
              </div>` : ''}
            <div class="citation-reasoning">
              <strong>Relevance:</strong> ${escHtml(clause.relevance || 'Referenced during evaluation')}
            </div>
          </div>
        </div>`;
    });
  }

  container.innerHTML = html;
}

// ── Item Analysis Tab ─────────────────────────────────────────────────────────
function renderItemAnalysis(exp) {
  const container = document.getElementById('items-analysis');
  const items = exp?.item_explanations || [];
  if (!items.length) {
    container.innerHTML = '<p class="muted-text">No item analysis available.</p>';
    return;
  }

  container.innerHTML = items.map(item => {
    const statusKey = (item.status || '').toLowerCase().replace(/_/g, '-');
    const statusLabel = (item.status || '').replace(/_/g, ' ');
    const deduction = item.amount - (item.approved_amount || 0);

    return `
      <div class="item-card">
        <div class="item-card-header">
          <span class="item-name">${escHtml(item.bill_item)}</span>
          <span class="item-status-chip ${statusKey}">${escHtml(statusLabel)}</span>
        </div>
        <div class="item-card-body">
          <div class="item-amounts">
            <div class="amount-row">
              <span class="akey">Billed</span>
              <span class="aval">${fmt(item.amount)}</span>
            </div>
            <div class="amount-row">
              <span class="akey">Approved</span>
              <span class="aval ${item.approved_amount > 0 ? 'approved-amt' : 'rejected-amt'}">${fmt(item.approved_amount)}</span>
            </div>
            ${deduction > 0 ? `
            <div class="amount-row">
              <span class="akey">Deduction</span>
              <span class="aval rejected-amt">-${fmt(deduction)}</span>
            </div>` : ''}
          </div>
          <div class="item-cite-block">
            <div class="item-cite-ref">
              ${item.page_number ? `<span class="cite-page-badge"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16"/><rect x="6" y="6" width="12" height="16" rx="1"/></svg> Pg. ${item.page_number}</span>` : ''}
              ${item.clause_section ? `<span class="cite-section-name">${escHtml(item.clause_section.replace(/_/g, ' '))}</span>` : ''}
              ${item.policy_reference ? `<span style="font-size:0.72rem; color:var(--text-muted);">${escHtml(item.policy_reference)}</span>` : ''}
            </div>
            <div class="item-reasoning-text">${escHtml(item.reasoning || '—')}</div>
          </div>
        </div>
      </div>`;
  }).join('');
}

// ── Simulation Tab ────────────────────────────────────────────────────────────
function renderSimulation(sim) {
  const container = document.getElementById('simulation-content');
  if (!sim || sim.status === 'unavailable') {
    container.innerHTML = `
      <div style="text-align:center; padding:40px; color:var(--text-muted);">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px; opacity:0.4;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        <p style="font-style:italic; font-size:0.88rem;">${escHtml(sim?.message || 'What-If simulation requires a processed claim.')}</p>
      </div>`;
    return;
  }

  if (sim.status === 'not_needed') {
    container.innerHTML = `
      <div style="background:#d1fae5; border:1.5px solid #10b981; border-radius:12px; padding:24px; text-align:center;">
        <div style="font-family:var(--font-serif); font-size:1.1rem; color:#065f46; margin-bottom:6px;">✓ Claim Fully Approved</div>
        <p style="font-size:0.85rem; color:#065f46; margin:0;">${escHtml(sim.message || 'No simulation needed.')}</p>
      </div>`;
    return;
  }

  const scenarios   = sim.scenarios || [];
  const priority    = sim.appeal_priority || [];
  const bestCase    = sim.best_case_approval;
  const currentApp  = sim.currently_approved;
  const totalBilled = sim.total_billed;
  const totalRej    = sim.total_rejected;
  const bestCasePct = sim.best_case_coverage_pct;

  const diffColor = { easy: '#10b981', medium: '#f59e0b', hard: '#ef4444' };
  const diffLabel = { easy: 'Easy', medium: 'Medium', hard: 'Hard' };

  container.innerHTML = `
    <!-- Summary bar -->
    <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:24px;">
      <div class="sim-stat-card">
        <div class="sim-stat-label">Currently Approved</div>
        <div class="sim-stat-value approved">${fmt(currentApp)}</div>
      </div>
      <div class="sim-stat-card">
        <div class="sim-stat-label">Total Rejected</div>
        <div class="sim-stat-value rejected">${fmt(totalRej)}</div>
      </div>
      <div class="sim-stat-card highlight">
        <div class="sim-stat-label">Best-Case Approval</div>
        <div class="sim-stat-value">${fmt(bestCase)}</div>
        <div class="sim-stat-sub">${bestCasePct?.toFixed(1) || 0}% coverage</div>
      </div>
    </div>

    <!-- Scenarios -->
    ${scenarios.length ? `
    <div style="margin-bottom:22px;">
      <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); margin-bottom:12px;">
        Appeal Scenarios
      </div>
      ${scenarios.map((s, i) => {
        const gain = s.potential_additional_approval || 0;
        const diff = s.difficulty || 'medium';
        const dc   = diffColor[diff] || '#94a3b8';
        return `
        <div class="sim-scenario-card">
          <div class="sim-scenario-header">
            <div style="display:flex; align-items:center; gap:10px; flex:1;">
              <div class="sim-scenario-num">${i + 1}</div>
              <div>
                <div style="font-weight:600; font-size:0.9rem;">${escHtml(s.title)}</div>
                <div style="font-size:0.78rem; color:var(--text-muted); margin-top:2px;">${escHtml(s.description)}</div>
              </div>
            </div>
            <div style="text-align:right; flex-shrink:0; margin-left:12px;">
              ${gain > 0 ? `<div style="font-family:var(--font-serif); font-size:1rem; font-weight:700; color:#10b981;">+${fmt(gain)}</div>` : ''}
              <div style="font-size:0.68rem; font-weight:600; color:${dc}; text-transform:uppercase; letter-spacing:0.06em; margin-top:2px;">
                ${diffLabel[diff] || diff} to implement
              </div>
            </div>
          </div>
          ${(s.action_items || []).length ? `
          <div class="sim-action-list">
            ${s.action_items.map(a => `<div class="sim-action-item">→ ${escHtml(a)}</div>`).join('')}
          </div>` : ''}
          ${s.new_approved_amount ? `
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:8px; border-top:1px solid var(--border); padding-top:8px;">
            New approved amount if implemented: <strong>${fmt(s.new_approved_amount)}</strong>
          </div>` : ''}
        </div>`;
      }).join('')}
    </div>` : ''}

    <!-- Appeal Priority -->
    ${priority.length ? `
    <div>
      <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); margin-bottom:12px;">
        Appeal Priority Items
      </div>
      <div class="priority-list">
        ${priority.map(p => `
        <div class="priority-item">
          <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0;">
            <span class="priority-badge ${(p.priority || 'MEDIUM').toLowerCase()}">${p.priority}</span>
            <div style="min-width:0;">
              <div style="font-size:0.84rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escHtml(p.item)}</div>
              <div style="font-size:0.73rem; color:var(--text-muted);">${escHtml(p.reason)}</div>
            </div>
          </div>
          <div style="font-family:var(--font-serif); font-weight:700; font-size:0.92rem; flex-shrink:0;">${fmt(p.amount)}</div>
        </div>`).join('')}
      </div>
    </div>` : ''}`;
}

// ── Fraud Tab ─────────────────────────────────────────────────────────────────
function renderFraud(fraud) {
  const container = document.getElementById('fraud-content');
  if (!fraud) {
    container.innerHTML = '<p class="muted-text">No fraud analysis available.</p>';
    return;
  }

  const score = fraud.fraud_risk_score || 0;
  const level = (fraud.risk_level || 'LOW').toUpperCase();
  const levelColor = { LOW: '#10b981', MEDIUM: '#f59e0b', HIGH: '#ef4444', CRITICAL: '#dc2626' }[level] || '#94a3b8';
  const r = 52, circ = 2 * Math.PI * r;
  const dashOffset = circ * (1 - score / 100);

  container.innerHTML = `
    <div class="fraud-overview">
      <div class="fraud-gauge-wrap">
        <div class="gauge-circle" style="width:130px; height:130px; position:relative;">
          <svg width="130" height="130" viewBox="0 0 130 130">
            <circle class="gauge-bg" cx="65" cy="65" r="${r}" fill="none" stroke-width="12"/>
            <circle class="gauge-value" cx="65" cy="65" r="${r}" fill="none"
              stroke="${levelColor}" stroke-width="12" stroke-linecap="round"
              stroke-dasharray="${circ.toFixed(1)}" stroke-dashoffset="${dashOffset.toFixed(1)}"
              style="transform-origin:65px 65px; transform:rotate(-90deg); transition:stroke-dashoffset 1s ease;"/>
          </svg>
          <div class="gauge-text" style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column;">
            <div style="font-family:var(--font-serif); font-size:1.5rem; font-weight:700; color:${levelColor}; line-height:1;">${score.toFixed(0)}</div>
            <div style="font-size:0.62rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">/ 100</div>
          </div>
        </div>
        <div class="fraud-level-label" style="color:${levelColor};">${level} RISK</div>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">${fraud.summary || ''}</div>
      </div>
      <div>
        <div style="font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-muted); margin-bottom:12px;">Detected Flags (${fraud.flags?.length || 0})</div>
        <div class="fraud-flags-list">
          ${(fraud.flags || []).length === 0
            ? '<div style="color:var(--text-muted); font-style:italic; font-size:0.85rem;">✓ No fraud indicators detected.</div>'
            : (fraud.flags || []).map(f => `
              <div class="fraud-flag-card">
                <span class="ff-severity ${(f.severity || 'low').toLowerCase()}">${escHtml(f.severity || 'LOW')}</span>
                <div class="ff-body">
                  <div class="ff-desc">${escHtml(f.description || f.flag_type || '—')}</div>
                  ${f.evidence ? `<div class="ff-ev">${escHtml(f.evidence)}</div>` : ''}
                </div>
              </div>`).join('')}
        </div>
        ${fraud.recommendation ? `
          <div style="margin-top:16px; background:#fef3c7; border:1px solid #f59e0b; border-radius:8px; padding:12px 14px; font-size:0.83rem; color:#92400e;">
            <strong>Recommendation:</strong> ${escHtml(fraud.recommendation)}
          </div>` : ''}
      </div>
    </div>`;
}

// ── History ───────────────────────────────────────────────────────────────────
function renderHistory() {
  const container = document.getElementById('history-list');
  if (!sessionHistory.length) {
    container.innerHTML = '<p class="muted-text" style="padding:20px 28px;">No claims processed yet this session.</p>';
    return;
  }

  container.innerHTML = sessionHistory.map(h => {
    const cls = (h.decision || '').toLowerCase().replace(/_/g, '-');
    return `
      <div class="history-item" onclick="reloadResult('${h.claim_id}')">
        <span class="history-decision ${cls}">${(h.decision || 'N/A').replace(/_/g, ' ')}</span>
        <div class="history-meta">
          <strong style="color:var(--text-primary);">${escHtml(h.bill_name)}</strong>
          <br>
          <span style="font-size:0.75rem;">Bill: ${fmt(h.amount)} → Approved: ${fmt(h.approved)}</span>
        </div>
        <span class="history-id">${escHtml(h.claim_id)}</span>
        <span class="history-time">${h.time}</span>
      </div>`;
  }).join('');
}

window.reloadResult = function(claimId) {
  const h = sessionHistory.find(x => x.claim_id === claimId);
  if (!h) return;
  setActiveNav(btnEval);
  hideAllSections();
  if (currentResult && currentResult.claim_id === claimId) {
    resultsSection.classList.remove('hidden');
  }
};

// ── Analytics ─────────────────────────────────────────────────────────────────
async function loadAnalytics() {
  const container = document.getElementById('analytics-content');
  container.innerHTML = '<p class="muted-text" style="padding:20px 28px;">Loading platform metrics…</p>';

  try {
    const resp = await fetch(`${API_BASE}/analytics/stats`);
    if (!resp.ok) throw new Error('Failed to load analytics');
    const stats = await resp.json();

    let langHtml = Object.entries(stats.language_distribution || {})
      .map(([lang, count]) => `<div style="display:flex; justify-content:space-between; font-size:0.8rem; padding:4px 0; border-bottom:1px solid var(--border-lt);"><span style="color:var(--text-muted);">${escHtml(lang)}</span><strong>${count}</strong></div>`)
      .join('') || '<div style="color:var(--text-muted); font-style:italic; font-size:0.8rem;">No data yet</div>';

    container.innerHTML = `
      <div class="analytics-grid">
        <div class="analytic-card">
          <div class="analytic-val">${stats.total_claims || 0}</div>
          <div class="analytic-lbl">Total Claims</div>
        </div>
        <div class="analytic-card">
          <div class="analytic-val" style="color:var(--approved);">${stats.approval_rate || 0}%</div>
          <div class="analytic-lbl">Approval Rate</div>
        </div>
        <div class="analytic-card">
          <div class="analytic-val">${fmt(stats.total_billed)}</div>
          <div class="analytic-lbl">Total Billed</div>
        </div>
        <div class="analytic-card">
          <div class="analytic-val" style="color:var(--approved);">${fmt(stats.total_approved)}</div>
          <div class="analytic-lbl">Total Approved</div>
        </div>
        <div class="analytic-card">
          <div class="analytic-val" style="color:var(--rejected);">${fmt(stats.total_savings)}</div>
          <div class="analytic-lbl">Total Savings</div>
        </div>
        <div class="analytic-card">
          <div class="analytic-val">${(stats.avg_processing_time_ms || 0).toFixed(0)}<span style="font-size:0.9rem; font-weight:400;">ms</span></div>
          <div class="analytic-lbl">Avg Speed</div>
        </div>
        <div class="analytic-card">
          <div class="analytic-val" style="color:var(--rejected);">${stats.high_fraud_flags || 0}</div>
          <div class="analytic-lbl">High Fraud Flags</div>
        </div>
        <div class="analytic-card" style="grid-column: span 1;">
          <div class="analytic-lbl" style="margin-bottom:10px;">Language Breakdown</div>
          ${langHtml}
        </div>
      </div>`;
  } catch (e) {
    container.innerHTML = `<p style="color:var(--rejected); padding:20px 28px;">${e.message}</p>`;
  }
}

// ── Evaluation ────────────────────────────────────────────────────────────────
btnEval.addEventListener('click', async () => {
  // If no current result navigate back to upload
  if (!currentResult) {
    hideAllSections();
    return;
  }
  // Already handled above; extra eval button runs evaluation benchmark
});

// Run evaluation benchmark via header button when Evaluate is held/double-clicked
btnEval.addEventListener('dblclick', async () => {
  setActiveNav(btnEval);
  uploadSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  historySection.classList.add('hidden');
  analyticsSection.classList.add('hidden');
  evalSection.classList.remove('hidden');
  await runEvaluation();
});

async function runEvaluation() {
  const container = document.getElementById('eval-results');
  container.innerHTML = '<p class="muted-text" style="padding:20px 28px;">Running evaluation benchmark on 200 synthetic claims…</p>';
  try {
    const resp = await fetch(`${API_BASE}/evaluation/run`, { method: 'POST' });
    if (!resp.ok) throw new Error('Evaluation failed');
    const data = await resp.json();
    renderEvalResults(data);
  } catch (e) {
    container.innerHTML = `<p style="color:var(--rejected); padding:20px 28px;">Evaluation error: ${e.message}</p>`;
  }
}

function renderEvalResults(d) {
  const container = document.getElementById('eval-results');
  const metrics = d.class_metrics || {};
  const cm = d.confusion_matrix || {};
  const classes = Object.keys(cm);

  container.innerHTML = `
    <div class="eval-content">
      <div class="eval-summary-grid">
        <div class="eval-stat">
          <div class="val">${((d.accuracy || 0) * 100).toFixed(1)}%</div>
          <div class="lbl">Accuracy</div>
        </div>
        <div class="eval-stat">
          <div class="val">${d.total_predictions || 0}</div>
          <div class="lbl">Total Claims</div>
        </div>
        <div class="eval-stat">
          <div class="val" style="color:var(--rejected);">${((d.false_rejection_rate || 0) * 100).toFixed(1)}%</div>
          <div class="lbl">False Rejection Rate</div>
        </div>
        <div class="eval-stat">
          <div class="val">${(d.processing_time_seconds || 0).toFixed(1)}s</div>
          <div class="lbl">Eval Runtime</div>
        </div>
      </div>
      <div style="overflow-x:auto; border:1px solid var(--border); border-radius:var(--r); margin:0 0 20px;">
        <table>
          <thead><tr>
            <th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th>
          </tr></thead>
          <tbody>
            ${Object.entries(metrics).map(([cls, m]) => `
              <tr>
                <td style="font-weight:600;">${escHtml(cls)}</td>
                <td style="font-family:var(--font-mono); text-align:center;">${(m.precision || 0).toFixed(3)}</td>
                <td style="font-family:var(--font-mono); text-align:center;">${(m.recall || 0).toFixed(3)}</td>
                <td style="font-family:var(--font-mono); text-align:center;">${(m.f1_score || 0).toFixed(3)}</td>
                <td style="font-family:var(--font-mono); text-align:center;">${m.support || 0}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
      ${classes.length ? `
        <div style="font-size:0.85rem; font-weight:700; color:var(--text-secondary); margin-bottom:10px;">Confusion Matrix</div>
        <div class="confusion-matrix">
          <table>
            <thead>
              <tr>
                <th>Actual \\ Predicted</th>
                ${classes.map(c => `<th>${escHtml(c)}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${classes.map(actual => `
                <tr>
                  <td style="font-weight:700; background:var(--cream);">${escHtml(actual)}</td>
                  ${classes.map(pred => {
                    const val = (cm[actual] || {})[pred] || 0;
                    const isDiag = actual === pred;
                    return `<td class="${isDiag ? 'diagonal' : (val > 0 ? 'off-diag' : '')}">${val}</td>`;
                  }).join('')}
                </tr>`).join('')}
            </tbody>
          </table>
        </div>` : ''}
    </div>`;
}

// ── Feedback Modal ────────────────────────────────────────────────────────────
const feedbackModal = document.getElementById('feedback-modal');
const closeFeedback = document.getElementById('close-feedback-modal');
const feedbackForm  = document.getElementById('feedback-form');
const feedbackMsg   = document.getElementById('feedback-result');

document.getElementById('btn-open-feedback')?.addEventListener('click', () => {
  if (!currentClaimId) return alert('Process a claim first.');
  feedbackModal.classList.remove('hidden');
  feedbackMsg.textContent = '';
  document.getElementById('feedback-comments').value = '';
});

closeFeedback?.addEventListener('click', () => feedbackModal.classList.add('hidden'));
feedbackModal?.addEventListener('click', e => { if (e.target === feedbackModal) feedbackModal.classList.add('hidden'); });

feedbackForm?.addEventListener('submit', async e => {
  e.preventDefault();
  const newDecision = document.getElementById('new-decision').value;
  const comments    = document.getElementById('feedback-comments').value.trim();
  if (!comments) return;

  try {
    const resp = await fetch(`${API_BASE}/analytics/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claim_id: currentClaimId, new_decision: newDecision, comments }),
    });
    if (!resp.ok) throw new Error('Feedback submission failed');
    feedbackMsg.textContent = '✓ Feedback submitted. Thank you.';
    feedbackMsg.style.color = '#059669';
    setTimeout(() => feedbackModal.classList.add('hidden'), 1800);
  } catch (err) {
    feedbackMsg.textContent = `Error: ${err.message}`;
    feedbackMsg.style.color = '#ef4444';
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────
(async function init() {
  try {
    const resp = await fetch(`${API_BASE}/health`);
    const data = await resp.json();
    const statusEl = document.getElementById('system-status');
    if (data.status === 'healthy') {
      statusEl.style.borderColor = 'rgba(16,185,129,0.4)';
      statusEl.querySelector('span:last-child').textContent = 'System Online';
    }
  } catch {
    const statusEl = document.getElementById('system-status');
    statusEl.style.borderColor = 'rgba(239,68,68,0.4)';
    statusEl.style.color = '#f87171';
    statusEl.style.background = 'rgba(239,68,68,0.1)';
    statusEl.querySelector('.status-dot').style.background = '#f87171';
    statusEl.querySelector('span:last-child').textContent = 'Server Offline';
  }
})();
