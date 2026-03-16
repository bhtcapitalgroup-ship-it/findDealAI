/**
 * RealDeal AI — Background Service Worker
 *
 * Orchestrates communication between content script, side panel, and backend API.
 * Manages caching and rate limiting.
 */

const API_BASE = "https://realdeal-ai-api.fly.dev/api/v1";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const MAX_CACHE_ENTRIES = 500;

/**
 * Open side panel when user clicks the extension icon.
 */
chrome.action.onClicked.addListener((tab) => {
  if (tab.url && tab.url.includes("zillow.com/homedetails")) {
    chrome.sidePanel.open({ tabId: tab.id });
  }
});

/**
 * Auto-open side panel when navigating to a Zillow listing.
 */
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === "complete" &&
    tab.url &&
    tab.url.includes("zillow.com/homedetails")
  ) {
    chrome.sidePanel.setOptions({
      tabId,
      path: "sidepanel/panel.html",
      enabled: true,
    });
  }
});

/**
 * Listen for property data from content script.
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PROPERTY_DATA") {
    handlePropertyData(message.payload, sender.tab?.id);
    sendResponse({ status: "received" });
  }

  if (message.type === "GET_ANALYSIS") {
    // Side panel requesting current analysis
    getLatestAnalysis(sender).then(sendResponse);
    return true; // Keep channel open for async response
  }

  if (message.type === "RECALCULATE") {
    // User changed assumptions — recalculate locally
    const metrics = calculateMetrics(
      message.payload.property,
      message.payload.rentEstimate,
      message.payload.assumptions
    );
    sendResponse({ metrics });
  }
});

/**
 * Handle incoming property data — check cache, then call API.
 */
async function handlePropertyData(propertyData, tabId) {
  const cacheKey = `analysis_${propertyData.zpid || propertyData.address}`;

  // Check cache first
  const cached = await getCached(cacheKey);
  if (cached) {
    console.log("[RealDeal] Cache hit for", cacheKey);
    broadcastToSidePanel(tabId, {
      type: "ANALYSIS_RESULT",
      payload: cached,
    });
    return;
  }

  // Notify side panel that we're loading
  broadcastToSidePanel(tabId, { type: "ANALYSIS_LOADING" });

  try {
    const analysis = await fetchAnalysis(propertyData);
    await setCache(cacheKey, analysis);
    broadcastToSidePanel(tabId, {
      type: "ANALYSIS_RESULT",
      payload: analysis,
    });
  } catch (error) {
    console.error("[RealDeal] Analysis failed:", error);

    // Fallback: calculate locally with 1% rule for rent
    const fallback = calculateLocalFallback(propertyData);
    broadcastToSidePanel(tabId, {
      type: "ANALYSIS_RESULT",
      payload: fallback,
      fallback: true,
    });
  }
}

/**
 * Call the backend API for full analysis.
 */
async function fetchAnalysis(propertyData) {
  // Map scraped field names to backend schema
  const payload = {
    address: propertyData.address,
    price: propertyData.price,
    beds: propertyData.beds,
    baths: propertyData.baths,
    sqft: propertyData.sqft,
    year_built: propertyData.yearBuilt,
    property_type: propertyData.propertyType,
    hoa: propertyData.hoa,
    zestimate: propertyData.zestimate,
    zpid: propertyData.zpid,
    zip_code: propertyData.zipCode,
    latitude: propertyData.latitude,
    longitude: propertyData.longitude,
  };

  const response = await fetch(`${API_BASE}/extension/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  // Normalize backend response to match side panel expectations
  const data = await response.json();
  return {
    property: data.property,
    rentEstimate: {
      amount: data.rent_estimate.amount,
      confidence: data.rent_estimate.confidence,
      source: data.rent_estimate.source,
      comps: data.rent_estimate.comps,
    },
    metrics: {
      capRate: data.metrics.cap_rate,
      noi: data.metrics.noi,
      monthlyMortgage: data.metrics.monthly_mortgage,
      monthlyCashFlow: data.metrics.monthly_cash_flow,
      annualCashFlow: data.metrics.annual_cash_flow,
      cashOnCash: data.metrics.cash_on_cash,
      totalCashInvested: data.metrics.total_cash_invested,
      brrrr: {
        arv: data.brrrr.arv,
        refiAmount: data.brrrr.refi_amount,
        cashLeftInDeal: data.brrrr.cash_left_in_deal,
        rating: data.brrrr.rating,
      },
      flip: {
        rehabEstimate: {
          low: data.flip.rehab_low,
          mid: Math.round((data.flip.rehab_low + data.flip.rehab_high) / 2),
          high: data.flip.rehab_high,
        },
        holdingCosts: data.flip.holding_costs,
        sellingCosts: data.flip.selling_costs,
        profit: data.flip.profit,
        roi: data.flip.roi,
        rating: data.flip.rating,
      },
    },
    neighborhood: data.neighborhood ? {
      crimeRate: data.neighborhood.crime_rate,
      crimeLabel: data.neighborhood.crime_label,
      schoolRating: data.neighborhood.school_rating,
      popGrowth: data.neighborhood.pop_growth,
      rentGrowth: data.neighborhood.rent_growth,
    } : null,
    verdict: data.verdict,
    investmentScore: data.investment_score,
    isFallback: false,
  };
}

/**
 * Local fallback when backend is unavailable.
 * Uses 1% rule for rent estimation and basic investment math.
 */
function calculateLocalFallback(property) {
  const rentEstimate = property.price * 0.008; // 0.8% conservative
  const metrics = calculateMetrics(property, rentEstimate, DEFAULT_ASSUMPTIONS);

  return {
    property,
    rentEstimate: {
      amount: Math.round(rentEstimate),
      confidence: "low",
      source: "1% rule estimate (offline)",
      comps: [],
    },
    metrics,
    neighborhood: null,
    verdict: null,
    isFallback: true,
  };
}

/**
 * Default investment assumptions.
 */
const DEFAULT_ASSUMPTIONS = {
  downPaymentPct: 0.25,
  interestRate: 0.07,
  loanTermYears: 30,
  vacancyRate: 0.08,
  maintenancePct: 0.01,
  insurancePct: 0.005,
  propertyTaxPct: 0.012,
  managementFeePct: 0.1,
};

/**
 * Calculate investment metrics.
 */
function calculateMetrics(
  property,
  monthlyRent,
  assumptions = DEFAULT_ASSUMPTIONS
) {
  const price = property.price;
  const hoa = property.hoa || 0;

  // Annual figures
  const annualRent = monthlyRent * 12;
  const annualVacancy = annualRent * assumptions.vacancyRate;
  const annualMaintenance = price * assumptions.maintenancePct;
  const annualInsurance = price * assumptions.insurancePct;
  const annualTax = price * assumptions.propertyTaxPct;
  const annualHoa = hoa * 12;
  const annualManagement = annualRent * assumptions.managementFeePct;

  const totalExpenses =
    annualVacancy +
    annualMaintenance +
    annualInsurance +
    annualTax +
    annualHoa +
    annualManagement;

  const noi = annualRent - totalExpenses;
  const capRate = (noi / price) * 100;

  // Mortgage calculation
  const loanAmount = price * (1 - assumptions.downPaymentPct);
  const monthlyRate = assumptions.interestRate / 12;
  const numPayments = assumptions.loanTermYears * 12;
  const monthlyMortgage =
    loanAmount *
    ((monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
      (Math.pow(1 + monthlyRate, numPayments) - 1));

  const monthlyCashFlow =
    monthlyRent -
    monthlyMortgage -
    annualTax / 12 -
    annualInsurance / 12 -
    hoa -
    (annualVacancy + annualMaintenance + annualManagement) / 12;

  const annualCashFlow = monthlyCashFlow * 12;
  const totalCashInvested =
    price * assumptions.downPaymentPct + price * 0.03; // 3% closing costs
  const cashOnCash = (annualCashFlow / totalCashInvested) * 100;

  // BRRRR analysis
  const arv = property.zestimate || price * 1.1;
  const refiAmount = arv * 0.75;
  const cashLeftInDeal = price * assumptions.downPaymentPct - (refiAmount - loanAmount);
  const brrrr = {
    arv,
    refiAmount: Math.round(refiAmount),
    cashLeftInDeal: Math.round(Math.max(0, cashLeftInDeal)),
    rating: cashLeftInDeal <= 0 ? "Excellent" :
            cashLeftInDeal / price < 0.1 ? "Good" :
            cashLeftInDeal / price < 0.2 ? "Fair" : "Poor",
  };

  // Flip analysis
  const rehabEstimate = estimateRehab(property);
  const holdingCosts = (monthlyMortgage + annualTax / 12 + annualInsurance / 12 + 200) * 6;
  const sellingCosts = arv * 0.08; // 6% commission + 2% closing
  const flipProfit = arv - price - rehabEstimate.mid - holdingCosts - sellingCosts;
  const flipRoi = (flipProfit / (price + rehabEstimate.mid)) * 100;
  const flip = {
    rehabEstimate,
    holdingCosts: Math.round(holdingCosts),
    sellingCosts: Math.round(sellingCosts),
    profit: Math.round(flipProfit),
    roi: Math.round(flipRoi * 10) / 10,
    rating: flipRoi > 25 ? "Excellent" :
            flipRoi > 15 ? "Good" :
            flipRoi > 5 ? "Marginal" : "Avoid",
  };

  return {
    capRate: Math.round(capRate * 100) / 100,
    noi: Math.round(noi),
    monthlyMortgage: Math.round(monthlyMortgage),
    monthlyCashFlow: Math.round(monthlyCashFlow),
    annualCashFlow: Math.round(annualCashFlow),
    cashOnCash: Math.round(cashOnCash * 100) / 100,
    totalCashInvested: Math.round(totalCashInvested),
    brrrr,
    flip,
  };
}

/**
 * Rough rehab estimate based on property age and size.
 */
function estimateRehab(property) {
  const sqft = property.sqft || 1500;
  const age = new Date().getFullYear() - (property.yearBuilt || 2000);

  let perSqft;
  if (age > 50) perSqft = { low: 25, mid: 45, high: 70 };
  else if (age > 30) perSqft = { low: 15, mid: 30, high: 50 };
  else if (age > 15) perSqft = { low: 10, mid: 20, high: 35 };
  else perSqft = { low: 5, mid: 12, high: 22 };

  return {
    low: Math.round(sqft * perSqft.low),
    mid: Math.round(sqft * perSqft.mid),
    high: Math.round(sqft * perSqft.high),
  };
}

/**
 * Send message to the side panel in the given tab.
 */
function broadcastToSidePanel(tabId, message) {
  chrome.runtime.sendMessage(message).catch(() => {
    // Side panel might not be open yet — that's ok
  });
}

/**
 * Get the latest analysis for the side panel when it opens.
 */
async function getLatestAnalysis(sender) {
  // The side panel will request analysis on load
  // We re-trigger extraction by messaging the content script
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tabs[0]) {
    chrome.tabs.sendMessage(tabs[0].id, { type: "RE_EXTRACT" }).catch(() => {});
  }
  return { status: "pending" };
}

// --- Cache helpers ---

async function getCached(key) {
  return new Promise((resolve) => {
    chrome.storage.local.get(key, (result) => {
      const entry = result[key];
      if (!entry) return resolve(null);
      if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
        chrome.storage.local.remove(key);
        return resolve(null);
      }
      resolve(entry.data);
    });
  });
}

async function setCache(key, data) {
  // Evict old entries if at capacity
  const all = await new Promise((r) => chrome.storage.local.get(null, r));
  const analysisKeys = Object.keys(all).filter((k) => k.startsWith("analysis_"));
  if (analysisKeys.length >= MAX_CACHE_ENTRIES) {
    const sorted = analysisKeys.sort(
      (a, b) => (all[a].timestamp || 0) - (all[b].timestamp || 0)
    );
    const toRemove = sorted.slice(0, Math.floor(MAX_CACHE_ENTRIES * 0.2));
    await new Promise((r) => chrome.storage.local.remove(toRemove, r));
  }

  return new Promise((resolve) => {
    chrome.storage.local.set(
      { [key]: { data, timestamp: Date.now() } },
      resolve
    );
  });
}
