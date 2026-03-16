/**
 * RealDeal AI — Side Panel Controller
 *
 * Renders analysis results received from the background service worker.
 */

let currentProperty = null;
let currentRentEstimate = null;

// --- Message listener ---

chrome.runtime.onMessage.addListener((message) => {
  switch (message.type) {
    case "ANALYSIS_LOADING":
      showLoading();
      break;
    case "ANALYSIS_RESULT":
      renderAnalysis(message.payload, message.fallback);
      break;
  }
});

// On load, request current analysis from background
chrome.runtime.sendMessage({ type: "GET_ANALYSIS" });

// --- UI State ---

function showLoading() {
  hide("empty-state");
  hide("results");
  show("loading");
}

function showResults() {
  hide("empty-state");
  hide("loading");
  show("results");
}

function show(id) {
  document.getElementById(id)?.classList.remove("hidden");
}

function hide(id) {
  document.getElementById(id)?.classList.add("hidden");
}

// --- Rendering ---

function renderAnalysis(data, isFallback) {
  showResults();

  currentProperty = data.property;
  currentRentEstimate = data.rentEstimate?.amount;

  // Address
  document.getElementById("address").textContent =
    data.property?.address || "Unknown address";

  // Property stats
  setText("stat-price", formatCurrency(data.property?.price));
  setText(
    "stat-bedbath",
    `${data.property?.beds || "—"} bd / ${data.property?.baths || "—"} ba`
  );
  setText("stat-sqft", data.property?.sqft ? formatNumber(data.property.sqft) : "—");
  setText("stat-year", data.property?.yearBuilt || "—");

  // Rent estimate
  renderRent(data.rentEstimate);

  // Investment metrics
  renderMetrics(data.metrics);

  // BRRRR
  renderBRRRR(data.metrics?.brrrr);

  // Flip
  renderFlip(data.metrics?.flip);

  // Neighborhood
  if (data.neighborhood) {
    renderNeighborhood(data.neighborhood);
  }

  // Verdict
  if (data.verdict) {
    renderVerdict(data.verdict, data.investmentScore);
  }

  // Risks & Opportunities
  if (data.verdict?.risks || data.verdict?.opportunities) {
    renderInsights(data.verdict.risks, data.verdict.opportunities);
  }

  // Fallback notice
  if (isFallback) {
    show("fallback-notice");
  } else {
    hide("fallback-notice");
  }
}

function renderRent(rent) {
  if (!rent) return;
  document.getElementById("rent-amount").textContent = formatCurrency(
    rent.amount,
    "/mo"
  );

  const conf = document.getElementById("rent-confidence");
  if (rent.confidence) {
    const pct =
      typeof rent.confidence === "number"
        ? `${rent.confidence}%`
        : rent.confidence;
    conf.textContent = `Confidence: ${pct}`;
  }

  const source = document.getElementById("rent-source");
  if (rent.source) {
    source.textContent = rent.source;
  }

  const compsEl = document.getElementById("rent-comps");
  if (rent.comps && rent.comps.length > 0) {
    compsEl.textContent = `${rent.comps.length} comparable${rent.comps.length > 1 ? "s" : ""} found`;
  }
}

function renderMetrics(metrics) {
  if (!metrics) return;

  setMetric("metric-caprate", `${metrics.capRate}%`, metrics.capRate, 6, 10);
  setMetric(
    "metric-cashflow",
    formatCurrency(metrics.monthlyCashFlow),
    metrics.monthlyCashFlow,
    0,
    500
  );
  setMetric("metric-coc", `${metrics.cashOnCash}%`, metrics.cashOnCash, 5, 12);
  setMetric(
    "metric-noi",
    formatCurrency(metrics.noi),
    metrics.noi,
    0,
    20000
  );
}

function setMetric(id, text, value, lowThreshold, highThreshold) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = "metric-value";
  if (value >= highThreshold) el.classList.add("positive");
  else if (value >= lowThreshold) el.classList.add("neutral");
  else el.classList.add("negative");
}

function renderBRRRR(brrrr) {
  if (!brrrr) return;
  const ratingEl = document.getElementById("brrrr-rating");
  ratingEl.textContent = brrrr.rating;
  ratingEl.style.color = ratingColor(brrrr.rating);

  setText("brrrr-arv", formatCurrency(brrrr.arv));
  setText("brrrr-refi", formatCurrency(brrrr.refiAmount));
  setText("brrrr-cash", formatCurrency(brrrr.cashLeftInDeal));
}

function renderFlip(flip) {
  if (!flip) return;
  const ratingEl = document.getElementById("flip-rating");
  ratingEl.textContent = flip.rating;
  ratingEl.style.color = ratingColor(flip.rating);

  setText("flip-profit", formatCurrency(flip.profit));
  setText("flip-roi", `${flip.roi}%`);
  setText(
    "flip-rehab",
    `${formatCurrency(flip.rehabEstimate?.low)} - ${formatCurrency(flip.rehabEstimate?.high)}`
  );
}

function renderNeighborhood(hood) {
  show("neighborhood-section");

  // Crime: lower is better (invert for bar)
  setBar("crime", 100 - (hood.crimeRate || 50), hood.crimeLabel || "—");
  setBar("schools", (hood.schoolRating || 5) * 10, hood.schoolRating ? `${hood.schoolRating}/10` : "—");
  setBar("pop", Math.min((hood.popGrowth || 0) * 20 + 50, 100), hood.popGrowth ? `${hood.popGrowth}%/yr` : "—");
  setBar("rent", Math.min((hood.rentGrowth || 0) * 10 + 50, 100), hood.rentGrowth ? `${hood.rentGrowth}%/yr` : "—");
}

function setBar(name, pct, label) {
  const fill = document.getElementById(`bar-${name}`);
  const labelEl = document.getElementById(`bar-${name}-label`);
  if (fill) fill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  if (labelEl) labelEl.textContent = label;
}

function renderVerdict(verdict, investmentScore) {
  const section = document.getElementById("verdict-section");
  section.classList.remove("hidden", "good", "average", "avoid");

  const level = verdict.verdict?.toLowerCase().replace(/\s+/g, "");
  if (level === "gooddeal" || level === "good") section.classList.add("good");
  else if (level === "average") section.classList.add("average");
  else section.classList.add("avoid");

  document.getElementById("verdict-badge").textContent =
    verdict.verdict || "—";
  document.getElementById("verdict-confidence").textContent = verdict.confidence
    ? `${verdict.confidence} Confidence`
    : "";
  document.getElementById("investment-score").textContent =
    investmentScore != null ? `Investment Score: ${investmentScore}/100` : "";
  document.getElementById("verdict-summary").textContent =
    verdict.summary || "";
}

function renderInsights(risks, opportunities) {
  show("risks-section");

  const risksList = document.getElementById("risks-list");
  const oppsList = document.getElementById("opps-list");

  risksList.innerHTML = "";
  oppsList.innerHTML = "";

  (risks || []).forEach((r) => {
    const li = document.createElement("li");
    li.textContent = r;
    risksList.appendChild(li);
  });

  (opportunities || []).forEach((o) => {
    const li = document.createElement("li");
    li.textContent = o;
    oppsList.appendChild(li);
  });
}

// --- Assumptions ---

function toggleAssumptions() {
  const body = document.getElementById("assumptions-body");
  const icon = document.getElementById("collapse-icon");
  body.classList.toggle("hidden");
  icon.style.transform = body.classList.contains("hidden")
    ? "rotate(0deg)"
    : "rotate(180deg)";
}

function recalculate() {
  if (!currentProperty || !currentRentEstimate) return;

  const assumptions = {
    downPaymentPct: parseFloat(document.getElementById("input-down").value) / 100,
    interestRate: parseFloat(document.getElementById("input-rate").value) / 100,
    vacancyRate: parseFloat(document.getElementById("input-vacancy").value) / 100,
    managementFeePct: parseFloat(document.getElementById("input-mgmt").value) / 100,
    maintenancePct: 0.01,
    insurancePct: 0.005,
    propertyTaxPct: 0.012,
    loanTermYears: 30,
  };

  chrome.runtime.sendMessage(
    {
      type: "RECALCULATE",
      payload: {
        property: currentProperty,
        rentEstimate: currentRentEstimate,
        assumptions,
      },
    },
    (response) => {
      if (response?.metrics) {
        renderMetrics(response.metrics);
        renderBRRRR(response.metrics.brrrr);
        renderFlip(response.metrics.flip);
      }
    }
  );
}

// --- Formatters ---

function formatCurrency(val, suffix = "") {
  if (val == null || isNaN(val)) return "—";
  const prefix = val < 0 ? "-" : "";
  const abs = Math.abs(val);
  if (abs >= 1000000) {
    return `${prefix}$${(abs / 1000000).toFixed(2)}M${suffix}`;
  }
  if (abs >= 1000) {
    return `${prefix}$${(abs / 1000).toFixed(abs >= 10000 ? 0 : 1)}K${suffix}`;
  }
  return `${prefix}$${Math.round(abs)}${suffix}`;
}

function formatNumber(val) {
  if (val == null) return "—";
  return val.toLocaleString();
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function ratingColor(rating) {
  switch (rating) {
    case "Excellent": return "var(--green)";
    case "Good": return "var(--green)";
    case "Fair": return "var(--yellow)";
    case "Marginal": return "var(--yellow)";
    case "Poor": return "var(--red)";
    case "Avoid": return "var(--red)";
    default: return "var(--text)";
  }
}
