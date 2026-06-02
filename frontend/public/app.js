
function buildCleanFormData(form) {
  const fd = new FormData();

  for (const element of form.elements) {
    if (!element.name || element.disabled) continue;

    if (element.type === "file") {
      if (element.files && element.files.length > 0) {
        fd.append(element.name, element.files[0]);
      }
      continue;
    }

    // Important fix:
    // Do not send blank optional numeric/text fields.
    // FastAPI receives blank numeric fields as "" and rejects them as validation errors.
    const value = (element.value ?? "").trim();
    if (value !== "") {
      fd.append(element.name, value);
    }
  }

  return fd;
}

function formatApiError(data) {
  if (!data) return "Unknown error";

  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => {
      const field = Array.isArray(d.loc) ? d.loc.join(".") : "field";
      return `${field}: ${d.msg}`;
    }).join("\n");
  }

  if (typeof data.detail === "string") return data.detail;
  if (typeof data.message === "string") return data.message;

  return JSON.stringify(data, null, 2);
}

async function postForm(url, form) {
  const fd = buildCleanFormData(form);
  const res = await fetch(apiUrl(url.replace(/^\/api/, "")), { method: "POST", body: fd });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(formatApiError(data));
  }
  return data;
}

function pretty(obj) {
  return JSON.stringify(obj, null, 2);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function apiUrl(path) {
  const base = (window.API_BASE || "").replace(/\/$/, "");
  return `${base}/api${path.startsWith("/") ? path : "/" + path}`;
}

async function apiGet(path, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(apiUrl(path), {
      cache: "no-store",
      signal: controller.signal,
      headers: { "Accept": "application/json" },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data));
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function setDropdownMessage(message) {
  const select = document.getElementById("compareBottleSelect");
  if (select) {
    select.style.display = "block";
    select.disabled = false;
    select.innerHTML = `<option value="">${escapeHtml(message)}</option>`;
  }
  setBottleDropdownStatus(message);
}

function setBottleDropdownStatus(message, kind = "info") {
  const el = document.getElementById("bottleDropdownStatus");
  if (!el) return;
  el.className = `helperText ${kind}`;
  el.textContent = message;
}


function openProcessingDialog() {
  const dlg = document.getElementById("processingDialog");
  if (dlg) dlg.classList.remove("hidden");
  setDialogResult("pending", "Processing...", "Waiting for comparison result.");
  setProcessingStep("capture");
  document.getElementById("gateResults").innerHTML = "Processing gate checks...";
  document.getElementById("dialogSummary").innerHTML = "Processing summary...";
  document.getElementById("parameterComparisonTable").innerHTML = "Processing parameters...";
  clearProcessingStatus();
  appendProcessingStatus("Processing dialog opened.", "INFO");
  const idBanner = document.getElementById("processingMatchIdBanner");
  if (idBanner) {
    idBanner.className = "processingIdBanner hidden";
    idBanner.innerHTML = "";
  }
}

function closeProcessingDialog() {
  const dlg = document.getElementById("processingDialog");
  if (dlg) dlg.classList.add("hidden");
}

function clearProcessingStatus() {
  const feed = document.getElementById("processingStatusFeed");
  if (feed) feed.innerHTML = "";
}

function appendProcessingStatus(message, status = "INFO") {
  const feed = document.getElementById("processingStatusFeed");
  if (!feed) return;
  const time = new Date().toLocaleTimeString();
  const div = document.createElement("div");
  div.className = `statusLine status-${status}`;
  div.innerHTML = `<span class="statusTime">${time}</span><span class="statusTag">${status}</span><span>${message}</span>`;
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}

function renderProcessingTrace(trace) {
  if (!trace || !trace.length) return;
  appendProcessingStatus(`Backend returned detailed processing trace with ${trace.length} status lines.`, "INFO");
  trace.forEach(item => {
    let displayMessage = `${item.step}: ${item.message}`;
    appendProcessingStatus(displayMessage, item.status || "INFO");
  });
}

function setProcessingStep(stepName) {
  const order = ["capture", "signature", "compare", "gates", "decision"];
  const currentIndex = order.indexOf(stepName);
  document.querySelectorAll(".step").forEach((el) => {
    const idx = order.indexOf(el.dataset.step);
    el.classList.remove("active", "done");
    if (idx < currentIndex) el.classList.add("done");
    if (idx === currentIndex) el.classList.add("active");
  });
}

function completeProcessingSteps() {
  document.querySelectorAll(".step").forEach((el) => {
    el.classList.remove("active");
    el.classList.add("done");
  });
}

function setDialogResult(kind, title, subtitle) {
  const el = document.getElementById("dialogFinalResult");
  if (!el) return;
  el.className = `finalResult ${kind}`;
  el.innerHTML = `<strong>${title}</strong><span>${subtitle || ""}</span>`;
}

function statusText(ok) {
  return ok ? "PASS" : "FAIL";
}

function gateBadge(ok) {
  return `<span class="statusBadge ${ok ? "pass" : "fail"}">${statusText(ok)}</span>`;
}

function renderGateResults(match) {
  const distinctiveAppearance = match.distinctive_appearance_gate;
  const preliminaryPhysical = match.preliminary_physical_gate;
  const controlledGeometry = match.controlled_geometry_gate;
  const color = match.color_gate;
  const primary = match.primary_identity_gate;
  const category = match.category_gate;
  const exact = match.exact_identifier_gate;
  const dlSeg = match.dl_segmentation_gate;
  const ml = match.ml_assisted_gate;

  return `
    <div class="gateList">
      <div class="gateItem">${gateBadge(distinctiveAppearance && distinctiveAppearance.passed)} <strong>Distinctive Object Appearance Gate</strong><small>${distinctiveAppearance ? `Pass Rate: ${Math.round((distinctiveAppearance.pass_rate || 0) * 100)}% | Appearance Parameters: ${distinctiveAppearance.compared_appearance_parameters || 0}` : "-"}</small></div>
      <div class="gateItem">${gateBadge(preliminaryPhysical && preliminaryPhysical.passed)} <strong>Preliminary Physical Characteristics Gate</strong><small>${preliminaryPhysical ? `Pass Rate: ${Math.round((preliminaryPhysical.pass_rate || 0) * 100)}% | Parameters: ${preliminaryPhysical.compared_physical_parameters || 0}` : "-"}</small></div>
      <div class="gateItem">${gateBadge(controlledGeometry && controlledGeometry.passed)} <strong>Controlled Geometry Gate</strong><small>${controlledGeometry ? `Pass Rate: ${Math.round((controlledGeometry.pass_rate || 0) * 100)}% | Mode: ${controlledGeometry.mode || "-"}` : "-"}</small></div>
      <div class="gateItem">${gateBadge(color && color.passed)} <strong>Color Gate</strong><small>${color ? `Pass Rate: ${Math.round((color.pass_rate || 0) * 100)}%` : "-"}</small></div>
      <div class="gateItem">${gateBadge(primary && primary.passed)} <strong>Primary Identity Gate</strong><small>${primary ? `Pass Rate: ${Math.round((primary.pass_rate || 0) * 100)}%` : "-"}</small></div>
      <div class="gateItem">${gateBadge(category && category.passed)} <strong>Category Gate</strong><small>${category ? `Failed Categories: ${(category.failed_categories || []).join(", ") || "-"}` : "-"}</small></div>
      <div class="gateItem">${gateBadge(dlSeg ? dlSeg.passed : true)} <strong>Light DL Segmentation Gate</strong><small>${dlSeg ? `Mode: ${dlSeg.mode} | Quality: ${dlSeg.average_quality_score} | Real Model: ${dlSeg.real_model_used ? "YES" : "NO"} | ONNX: ${dlSeg.onnx_used ? "YES" : "NO"}` : "-"}</small></div>
      <div class="gateItem">${gateBadge(ml ? ml.passed : true)} <strong>ML-Assisted Feature Gate</strong><small>${ml ? (ml.enabled ? `Cosine: ${ml.cosine_similarity} | Euclidean: ${ml.euclidean_similarity} | Features: ${ml.compared_ml_features}` : ml.reason) : "-"}</small></div>
      <div class="gateItem">${gateBadge(exact && exact.passed)} <strong>Exact Identifier Gate</strong><small>${exact ? `Compared: ${exact.compared_exact_parameters || 0}` : "-"}</small></div>
    </div>
  `;
}


function renderOverlayAssets(data) {
  const visual = data.visual_assets || (data.full_result ? data.full_result.visual_assets : null) || {};
  const masterViews = ((visual.master || {}).views) || {};
  const observedViews = ((visual.observed || {}).views) || {};
  const allViews = ["front", "side", "top"].filter(v => masterViews[v] || observedViews[v]);
  if (!allViews.length) return "";

  return `
    <div class="overlaySection">
      <h4>Image Overlay Visualization</h4>
      <p>Green mask, yellow contour, orange bottle box, and highlighted cap/label/body regions are shown below.</p>
      ${allViews.map(v => `
        <div class="overlayCompareBlock">
          <h5>${v.charAt(0).toUpperCase() + v.slice(1)} View</h5>
          <div class="overlayGrid">
            ${masterViews[v] ? `
              <div class="overlayCard">
                <strong>Registered Bottle Overlay</strong>
                <img src="/api${masterViews[v].overlay_url}" alt="master ${v} overlay" />
                <small>Mode: ${masterViews[v].segmentation_mode || '-'} | Quality: ${masterViews[v].segmentation_quality || '-'}</small>
              </div>` : ``}
            ${observedViews[v] ? `
              <div class="overlayCard">
                <strong>Observed Bottle Overlay</strong>
                <img src="/api${observedViews[v].overlay_url}" alt="observed ${v} overlay" />
                <small>Mode: ${observedViews[v].segmentation_mode || '-'} | Quality: ${observedViews[v].segmentation_quality || '-'}</small>
              </div>` : ``}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function renderDialogSummary(data) {
  const m = data.match;
  const reasons = m.no_match_reasons && m.no_match_reasons.length
    ? `<ul>${m.no_match_reasons.map(r => `<li>${r}</li>`).join("")}</ul>`
    : "<p>No blocking mismatch reasons.</p>";

  return `
    <p><strong>Processing Bottle Match ID:</strong> ${data.processing_match_id || "-"}</p>
    <p><strong>Registered Bottle:</strong> ${data.brand || ""} ${data.product_name || ""}</p>
    <p><strong>Bottle ID:</strong> ${data.bottle_id}</p>
    <p><strong>Decision:</strong> ${m.decision}</p>
    <p><strong>Score:</strong> ${m.score_percent}%</p>
    <p><strong>Compared Parameters:</strong> ${m.compared_parameters}</p>
    <p><strong>Minimum Required Score:</strong> ${m.minimum_required_score_percent}%</p>
    <h4>No Match Reasons</h4>
    ${reasons}
  `;
}

function renderParameterComparison(details) {
  if (!details || !details.length) {
    return "<p>No parameter details returned.</p>";
  }

  const rows = details.map((d) => {
    const result = d.in_tolerance ? "PASS" : "FAIL";
    return `
      <tr class="${d.in_tolerance ? "rowPass" : "rowFail"}">
        <td>${d.label || d.key}<br><small>${d.key}</small></td>
        <td>${d.category || "-"}</td>
        <td>${d.master_value}</td>
        <td>${d.observed_value}</td>
        <td>${d.tolerance}</td>
        <td>${Math.round((d.score || 0) * 100)}%</td>
        <td><span class="statusBadge ${d.in_tolerance ? "pass" : "fail"}">${result}</span></td>
      </tr>
    `;
  }).join("");

  return `
    <table class="paramCompareTable">
      <thead>
        <tr>
          <th>Parameter</th>
          <th>Category</th>
          <th>Registered Value</th>
          <th>Observed Value</th>
          <th>Tolerance</th>
          <th>Parameter Score</th>
          <th>Result</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}


function renderStoredProcessingMatchDialog(item) {
  const full = item.full_result || {};
  const match = full.match || {
    decision: item.decision,
    score_percent: item.score_percent,
    compared_parameters: item.compared_parameters,
    no_match_reasons: item.no_match_reasons,
    distinctive_appearance_gate: item.gate_results ? item.gate_results.distinctive_appearance_gate : null,
    preliminary_physical_gate: item.gate_results ? item.gate_results.preliminary_physical_gate : null,
    controlled_geometry_gate: item.gate_results ? item.gate_results.controlled_geometry_gate : null,
    color_gate: item.gate_results ? item.gate_results.color_gate : null,
    primary_identity_gate: item.gate_results ? item.gate_results.primary_identity_gate : null,
    category_gate: item.gate_results ? item.gate_results.category_gate : null,
    exact_identifier_gate: item.gate_results ? item.gate_results.exact_identifier_gate : null,
    dl_segmentation_gate: item.gate_results ? item.gate_results.dl_segmentation_gate : null,
    ml_assisted_gate: item.gate_results ? item.gate_results.ml_assisted_gate : null,
    details: item.parameter_details || []
  };

  const data = {
    processing_match_id: item.processing_match_id,
    bottle_id: item.bottle_id,
    brand: item.brand,
    product_name: item.product_name,
    observed_signature: item.observed_signature,
    match,
    visual_assets: full.visual_assets || item.visual_assets || {},
    processing_trace: full.processing_trace || item.processing_trace || []
  };

  openProcessingDialog();
  completeProcessingSteps();
  updateProcessingDialogWithResult(data);

  const summary = document.getElementById("dialogSummary");
  if (summary) {
    summary.innerHTML += `
      <h4>Stored Record Details</h4>
      <p><strong>Stored At:</strong> ${item.created_at || "-"}</p>
      <p><strong>Source:</strong> Audit log / Processing Bottle Match table</p>
      <details>
        <summary>View Full Stored JSON</summary>
        <pre>${JSON.stringify(item, null, 2)}</pre>
      </details>
    `;
  }
}

async function openProcessingMatchRecord(processingMatchId) {
  try {
    openProcessingDialog();
    setDialogResult("pending", "Loading Stored Processing Match", processingMatchId);
    setProcessingStep("decision");

    const res = await fetch(apiUrl(`/processing-matches/${encodeURIComponent(processingMatchId)}`));
    const item = await res.json();

    if (!res.ok) {
      throw new Error(formatApiError(item));
    }

    renderStoredProcessingMatchDialog(item);
  } catch (err) {
    updateProcessingDialogWithError(err.message);
  }
}


function updateProcessingDialogWithResult(data) {
  const m = data.match;
  const kind = m.decision === "CONFIRMED_MATCH" || m.decision === "MATCH"
    ? "success"
    : "fail";

  setDialogResult(
    kind,
    m.decision,
    `Score ${m.score_percent}% across ${m.compared_parameters} compared parameters`
  );

  clearProcessingStatus();
  appendProcessingStatus("Processing dialog opened.", "INFO");
  const idBanner = document.getElementById("processingMatchIdBanner");
  if (idBanner) {
    idBanner.className = "processingIdBanner";
    idBanner.innerHTML = `<strong>Processing Bottle Match ID:</strong> ${data.processing_match_id || "-"}`;
  }

  document.getElementById("gateResults").innerHTML = renderGateResults(m);
  document.getElementById("dialogSummary").innerHTML = renderDialogSummary(data) + renderOverlayAssets(data);
  renderProcessingTrace(data.processing_trace);
  document.getElementById("parameterComparisonTable").innerHTML = renderParameterComparison(m.details);
  completeProcessingSteps();
}

function updateProcessingDialogWithError(message) {
  setDialogResult("fail", "ERROR", message);
  document.getElementById("dialogSummary").innerHTML = `<p>${message}</p>`;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}


function decisionClass(decision) {
  if (!decision) return "";
  if (decision.includes("CONFIRMED") || decision.includes("HIGH_CONFIDENCE")) return "confirmed";
  if (decision.includes("NO_MATCH") || decision.includes("SUSPICIOUS")) return "nomatch";
  return "review";
}

document.getElementById("registerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const out = document.getElementById("registerOutput");
  out.textContent = "Registering bottle signature...";
  try {
    const data = await postForm("/api/bottles/register", e.target);
    out.textContent = pretty(data);
    await loadBottles();
    await loadLogs();
    await loadProcessingMatches();
  } catch (err) {
    out.textContent = "Error: " + err.message;
  }
});

document.getElementById("identifyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const out = document.getElementById("identifyOutput");
  const card = document.getElementById("matchCard");
  const bottleId = document.getElementById("compareBottleSelect").value;

  card.className = "match hidden";

  if (!bottleId) {
    out.textContent = "Error: Select a registered bottle to compare against.";
    setBottleDropdownStatus("Select a registered bottle before comparing. If the list is empty, register a master bottle first.", "error");
    openProcessingDialog();
    updateProcessingDialogWithError("Select a registered bottle to compare against.");
    return;
  }

  openProcessingDialog();
  out.textContent = "Comparison started. Detailed processing is shown in the dialog.";

  try {
    setProcessingStep("capture");
    appendProcessingStatus("Validating selected registered bottle and required front/side/top photos.", "INFO");
    await delay(250);

    setProcessingStep("signature");
    appendProcessingStatus("Preparing uploaded test sample for physical observation and signature recreation.", "INFO");
    appendProcessingStatus("Checking registered bottle selection and form inputs.", "INFO");
    appendProcessingStatus("Ensuring front/side/top files are attached.", "INFO");
    await delay(250);

    setProcessingStep("compare");
    appendProcessingStatus("Calling backend comparison engine. Extracting object characteristics, segmentation mask, geometry and ML features.", "INFO");
    appendProcessingStatus("Observing object-level physical characteristics for preliminary gate.", "INFO");
    appendProcessingStatus("Computing image-derived signature parameters from all three axes.", "INFO");
    appendProcessingStatus("Generating overlay visuals for registered and observed bottle views.", "INFO");
    const data = await postForm(`/api/compare/${bottleId}`, e.target);
    out.textContent = pretty(data);

    setProcessingStep("gates");
    appendProcessingStatus("Applying preliminary physical characteristics gate first.", "INFO");
    appendProcessingStatus("Each parameter check will be listed below after the backend returns.", "INFO");
    appendProcessingStatus("Applying controlled geometry, color, primary identity, DL segmentation and ML-assisted gates.", "INFO");
    await delay(250);

    setProcessingStep("decision");
    appendProcessingStatus("Rendering final decision, text comparison, overlays and parameter-level pass/fail table.", "INFO");
    appendProcessingStatus("Streaming every returned gate and parameter check into the processing status feed.", "INFO");
    updateProcessingDialogWithResult(data);

    const m = data.match;
    if (m) {
      card.className = "match " + decisionClass(m.decision);
      card.innerHTML = `
        <h3>Comparison Result: ${data.brand || ""} ${data.product_name || ""}</h3>
        <p><strong>Processing Bottle Match ID:</strong> ${data.processing_match_id || "-"}</p>
        <p><strong>Registered Bottle ID:</strong> ${data.bottle_id}</p>
        <p><strong>Decision:</strong> ${m.decision}</p>
        <p><strong>Score:</strong> ${m.score_percent}% | <strong>Compared Parameters:</strong> ${m.compared_parameters}</p>
        <p><strong>No Match Reasons:</strong> ${(m.no_match_reasons && m.no_match_reasons.length) ? m.no_match_reasons.join(", ") : "-"}</p>
        <p><strong>Appearance:</strong> ${m.distinctive_appearance_gate ? (m.distinctive_appearance_gate.passed ? "PASS" : "FAIL") : "-"} | 
           <strong>Preliminary Physical:</strong> ${m.preliminary_physical_gate ? (m.preliminary_physical_gate.passed ? "PASS" : "FAIL") : "-"} | 
           <strong>Controlled Geometry:</strong> ${m.controlled_geometry_gate ? (m.controlled_geometry_gate.passed ? "PASS" : "FAIL") : "-"} | 
           <strong>Color Gate:</strong> ${m.color_gate ? (m.color_gate.passed ? "PASS" : "FAIL") : "-"} | 
           <strong>Primary Gate:</strong> ${m.primary_identity_gate ? (m.primary_identity_gate.passed ? "PASS" : "FAIL") : "-"} | 
           <strong>Category Gate:</strong> ${m.category_gate ? (m.category_gate.passed ? "PASS" : "FAIL") : "-"} | 
           <strong>DL Gate:</strong> ${m.dl_segmentation_gate ? (m.dl_segmentation_gate.passed ? "PASS" : "FAIL") : "-"}</p>
      `;
    }

    await loadLogs();
    await loadProcessingMatches();
  } catch (err) {
    out.textContent = "Error: " + err.message;
    updateProcessingDialogWithError(err.message);
  }
});


async function loadRuntimeConfig() {
  try {
    const cfg = await apiGet("/runtime/config", 5000);
    const el = document.getElementById("processingModeNote");
    if (el) {
      el.textContent = `Mode: ${cfg.processing_mode}. OCR: ${cfg.enable_ocr ? "ON" : "OFF"}. Overlays: ${cfg.enable_overlays ? "ON" : "OFF"}. Real DL: ${cfg.enable_real_dl ? "ON" : "OFF"}. Max image dimension: ${cfg.max_image_dim}.`;
    }
  } catch (err) {
    const el = document.getElementById("processingModeNote");
    if (el) el.textContent = "Could not load runtime config: " + err.message;
  }
}

async function createDemoData() {
  const out = document.getElementById("registerOutput");
  if (out) out.textContent = "Creating demo bottle data...";
  setBottleDropdownStatus("Creating demo bottle records...", "info");

  try {
    const res = await fetch(apiUrl("/demo/create"), { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(formatApiError(data));

    if (out) out.textContent = pretty(data);
    setBottleDropdownStatus(`Demo data ready. Created ${data.created_count || 0}, skipped ${data.skipped_count || 0}.`, "success");

    await loadBottles();
    await loadLogs();
    await loadProcessingMatches();
  } catch (err) {
    if (out) out.textContent = "Error creating demo data: " + err.message;
    setBottleDropdownStatus("Could not create demo data: " + err.message, "error");
  }
}

async function loadBottles() {
  const el = document.getElementById("bottleList");
  const select = document.getElementById("compareBottleSelect");

  if (el) el.innerHTML = "Loading registered bottle signatures...";
  if (select) {
    select.style.display = "block";
    select.disabled = false;
    select.innerHTML = `<option value="">Loading registered bottles...</option>`;
  }
  setBottleDropdownStatus("Loading registered bottle list from backend...", "info");

  try {
    const data = await apiGet("/bottles", 10000);
    const bottles = Array.isArray(data.bottles) ? data.bottles : [];

    if (select) {
      select.style.display = "block";
      select.disabled = false;

      if (!bottles.length) {
        select.innerHTML = `<option value="">No registered bottles available</option>`;
        setBottleDropdownStatus("No registered bottles found. Register a master bottle first.", "warn");
      } else {
        select.innerHTML =
          `<option value="">Select registered bottle...</option>` +
          bottles.map(b => {
            const brand = escapeHtml(b.brand || "Unknown brand");
            const product = escapeHtml(b.product_name || "Unknown product");
            const sku = escapeHtml(b.sku_code || "-");
            const qty = b.quantity_ml || "-";
            return `<option value="${b.id}">${brand} — ${product} | SKU: ${sku} | ${qty} ml</option>`;
          }).join("");
        setBottleDropdownStatus(`${bottles.length} registered bottle(s) loaded. Select one before comparison.`, "success");
      }
    }

    if (!el) return;

    if (!bottles.length) {
      el.innerHTML = `
        <p>No bottle signatures registered yet. Register a master bottle first.</p>
        <button class="secondary" onclick="loadBottles()">Refresh Registered Bottles</button>
      `;
      return;
    }

    el.innerHTML = bottles.map(b => `
      <div class="bottleRow">
        <div>
          <strong>${escapeHtml(b.brand || "")} — ${escapeHtml(b.product_name || "")}</strong>
          <small>SKU: ${escapeHtml(b.sku_code || "-")} | Qty: ${b.quantity_ml || "-"} ml | Parameters: ${b.signature_parameter_count || 0} | Created: ${escapeHtml(b.created_at || "-")}</small>
        </div>
        <button class="secondary" onclick="viewBottle(${b.id})">View Signature</button>
      </div>
    `).join("");
  } catch (err) {
    const msg = err.name === "AbortError" ? "request timed out" : err.message;
    if (select) {
      select.style.display = "block";
      select.disabled = false;
      select.innerHTML = `<option value="">Could not load bottles</option>`;
    }
    setBottleDropdownStatus(`Could not load bottles: ${msg}`, "error");
    if (el) {
      el.innerHTML = `
        <div class="errorBox">
          <strong>Could not load registered bottle list.</strong>
          <p>${escapeHtml(msg)}</p>
          <p>Backend target: ${escapeHtml(window.API_TARGET_LABEL || "http://localhost:8000")}</p>
          <p>Open these test URLs:</p>
          <pre>http://localhost:8000/bottles
http://localhost:3000/api/bottles</pre>
          <button class="secondary" onclick="loadBottles()">Retry Loading Bottles</button>
        </div>
      `;
    }
  }
}

async function viewBottle(id) {
  const res = await fetch(apiUrl(`/bottles/${id}`));
  const data = await res.json();
  alert(JSON.stringify(data.signature, null, 2).slice(0, 4000));
}

document.getElementById("refreshBtn").addEventListener("click", loadBottles);

document.getElementById("loadParamsBtn").addEventListener("click", async () => {
  const el = document.getElementById("paramList");
  el.innerHTML = "Loading parameters...";
  const res = await fetch(apiUrl("/parameters"));
  const data = await res.json();
  el.innerHTML = data.parameters.map(p => `<span class="param">${p.key} (${p.category})</span>`).join("");
});

function bootApp() {
  loadRuntimeConfig();
  loadBottles();
  loadLogs();
  loadProcessingMatches();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootApp);
} else {
  bootApp();
}


async function loadLogs() {
  const el = document.getElementById("logsList");
  if (!el) return;
  el.innerHTML = "Loading logs...";
  try {
    const res = await fetch(apiUrl("/logs?limit=100"));
    const data = await res.json();
    if (!data.logs.length) {
      el.innerHTML = "<p>No logs captured yet.</p>";
      return;
    }
    el.innerHTML = data.logs.map(log => {
      const processingMatchId = log.response && log.response.processing_match_id;
      const processingLink = processingMatchId
        ? `<p><strong>Processing Bottle Match:</strong> <button class="linkButton" type="button" onclick="openProcessingMatchRecord('${processingMatchId}')">${processingMatchId}</button></p>`
        : "";

      return `
        <div class="logRow">
          <div>
            <strong>${log.event_type}</strong>
            <span class="pill">${log.status}</span>
            <small>${log.created_at}</small>
            <p>${log.message || ""}</p>
            ${processingLink}
          </div>
          <details>
            <summary>Details</summary>
            <pre>${JSON.stringify({request: log.request, response: log.response}, null, 2)}</pre>
          </details>
        </div>
      `;
    }).join("");
  } catch (err) {
    el.innerHTML = "Error: " + err.message;
  }
}

async function clearLogs() {
  if (!confirm("Clear all logs?")) return;
  await fetch(apiUrl("/logs"), { method: "DELETE" });
  await loadLogs();
}


const createDemoDataBtn = document.getElementById("createDemoDataBtn");
if (createDemoDataBtn) createDemoDataBtn.addEventListener("click", createDemoData);

const refreshLogsBtn = document.getElementById("refreshLogsBtn");
if (refreshLogsBtn) refreshLogsBtn.addEventListener("click", loadLogs);

const clearLogsBtn = document.getElementById("clearLogsBtn");
if (clearLogsBtn) clearLogsBtn.addEventListener("click", clearLogs);



async function loadProcessingMatches() {
  const el = document.getElementById("processingMatchesList");
  if (!el) return;
  el.innerHTML = "Loading processing match records...";
  try {
    const res = await fetch(apiUrl("/processing-matches?limit=100"));
    const data = await res.json();
    if (!data.processing_matches.length) {
      el.innerHTML = "<p>No processing bottle match records yet.</p>";
      return;
    }

    el.innerHTML = data.processing_matches.map(item => `
      <div class="processingRecord">
        <div>
          <button class="linkButton strongLink" type="button" onclick="openProcessingMatchRecord('${item.processing_match_id}')">${item.processing_match_id}</button>
          <span class="pill">${item.decision}</span>
          <small>${item.created_at}</small>
          <p>${item.brand || ""} ${item.product_name || ""} | Score: ${item.score_percent || 0}% | Parameters: ${item.compared_parameters || 0}</p>
          <p><strong>No Match Reasons:</strong> ${(item.no_match_reasons && item.no_match_reasons.length) ? item.no_match_reasons.join(", ") : "-"}</p>
        </div>
        <details>
          <summary>View Stored Processing Details</summary>
          <pre>${JSON.stringify({
            request: item.request,
            gate_results: item.gate_results,
            observed_signature: item.observed_signature,
            parameter_details: item.parameter_details,
            full_result: item.full_result
          }, null, 2)}</pre>
        </details>
      </div>
    `).join("");
  } catch (err) {
    el.innerHTML = "Error: " + err.message;
  }
}

const refreshProcessingMatchesBtn = document.getElementById("refreshProcessingMatchesBtn");
if (refreshProcessingMatchesBtn) refreshProcessingMatchesBtn.addEventListener("click", loadProcessingMatches);

// Delegated modal close handler.
// This fixes the close button issue because the dialog HTML appears after the script tag in the page.
document.addEventListener("click", (event) => {
  if (
    event.target.id === "dialogCloseBtn" ||
    event.target.id === "dialogCloseBtnBottom" ||
    event.target.id === "processingDialog"
  ) {
    closeProcessingDialog();
  }
});
