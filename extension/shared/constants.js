/**
 * RealDeal AI — Shared Constants
 */

// Backend API
export const API_BASE =
  typeof chrome !== "undefined" && chrome.storage
    ? "http://localhost:8000/api/v1"
    : "http://localhost:8000/api/v1";

// Zillow DOM selectors — ordered by reliability
export const SELECTORS = {
  price: [
    '[data-testid="price"] span',
    ".ds-summary-row .ds-value",
    'span[data-testid="price"]',
  ],
  beds: [
    '[data-testid="bed-bath-beyond"] span:first-child',
    ".ds-bed-bath-table .ds-value:nth-child(1)",
  ],
  baths: [
    '[data-testid="bed-bath-beyond"] span:nth-child(2)',
    ".ds-bed-bath-table .ds-value:nth-child(2)",
  ],
  sqft: [
    '[data-testid="bed-bath-beyond"] span:nth-child(3)',
    ".ds-bed-bath-table .ds-value:nth-child(3)",
  ],
  address: [
    "h1.ds-address-container",
    '[data-testid="bdp-property-card"] h1',
    "h1",
  ],
  zestimate: ['[data-testid="zestimate-text"]', ".zestimate-value"],
};

// Cache settings
export const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
export const MAX_CACHE_ENTRIES = 500;

// Investment defaults
export const DEFAULT_ASSUMPTIONS = {
  downPaymentPct: 0.25,
  interestRate: 0.07,
  loanTermYears: 30,
  vacancyRate: 0.08,
  maintenancePct: 0.01,
  insurancePct: 0.005,
  propertyTaxPct: 0.012,
  managementFeePct: 0.1,
};

// Rating thresholds
export const THRESHOLDS = {
  capRate: { bad: 4, ok: 6, good: 8 },
  cashFlow: { bad: -100, ok: 0, good: 300 },
  cashOnCash: { bad: 3, ok: 6, good: 10 },
  brrrr: { poor: 30, fair: 50, good: 70, excellent: 85 },
  flipRoi: { avoid: 5, marginal: 15, good: 25 },
};
