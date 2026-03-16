/**
 * RealDeal AI — Formatting Utilities
 */

/**
 * Format a number as currency.
 * @param {number} val
 * @param {string} suffix - e.g. "/mo"
 * @returns {string}
 */
function formatCurrency(val, suffix = "") {
  if (val == null || isNaN(val)) return "—";
  const prefix = val < 0 ? "-" : "";
  const abs = Math.abs(val);
  if (abs >= 1_000_000) {
    return `${prefix}$${(abs / 1_000_000).toFixed(2)}M${suffix}`;
  }
  if (abs >= 10_000) {
    return `${prefix}$${Math.round(abs / 1_000)}K${suffix}`;
  }
  if (abs >= 1_000) {
    return `${prefix}$${(abs / 1_000).toFixed(1)}K${suffix}`;
  }
  return `${prefix}$${Math.round(abs)}${suffix}`;
}

/**
 * Format a number with locale-aware commas.
 */
function formatNumber(val) {
  if (val == null) return "—";
  return val.toLocaleString("en-US");
}

/**
 * Format a percentage.
 * @param {number} val - The percentage value (e.g. 8.5 for 8.5%)
 * @param {number} decimals
 */
function formatPercent(val, decimals = 1) {
  if (val == null || isNaN(val)) return "—";
  return `${val.toFixed(decimals)}%`;
}

/**
 * Get color for a rating string.
 */
function ratingColor(rating) {
  const colors = {
    Excellent: "var(--green)",
    Good: "var(--green)",
    Fair: "var(--yellow)",
    Marginal: "var(--yellow)",
    Average: "var(--yellow)",
    Poor: "var(--red)",
    Avoid: "var(--red)",
  };
  return colors[rating] || "var(--text)";
}

/**
 * Get color class based on metric value and thresholds.
 * @param {number} val
 * @param {number} low - below this is negative
 * @param {number} high - above this is positive
 * @returns {"positive"|"neutral"|"negative"}
 */
function metricColorClass(val, low, high) {
  if (val >= high) return "positive";
  if (val >= low) return "neutral";
  return "negative";
}

// Export for non-module usage
if (typeof globalThis !== "undefined") {
  globalThis.RealDealFormat = {
    formatCurrency,
    formatNumber,
    formatPercent,
    ratingColor,
    metricColorClass,
  };
}
