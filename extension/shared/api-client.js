/**
 * RealDeal AI — Backend API Client
 *
 * Wraps fetch calls to the backend with error handling,
 * timeout, and retry logic.
 */

const API_BASE = "https://realdeal-ai-api.fly.dev/api/v1";
const REQUEST_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2;

/**
 * Analyze a property via the backend.
 * @param {Object} propertyData - Scraped property data
 * @returns {Promise<Object>} Full analysis response
 */
async function analyzeProperty(propertyData) {
  return apiPost("/extension/analyze", {
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
  });
}

/**
 * POST request with timeout and retry.
 */
async function apiPost(path, body, retries = MAX_RETRIES) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      throw new ApiError(response.status, errorText);
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);

    // Retry on network errors or 5xx
    if (retries > 0 && isRetryable(error)) {
      console.warn(
        `[RealDeal] API call failed, retrying (${retries} left):`,
        error.message
      );
      await delay(1000);
      return apiPost(path, body, retries - 1);
    }

    throw error;
  }
}

/**
 * GET request with timeout.
 */
async function apiGet(path) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new ApiError(response.status);
    }
    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

/**
 * Health check — verify backend is reachable.
 */
async function checkHealth() {
  try {
    const data = await apiGet("/../health");
    return data.status === "healthy";
  } catch {
    return false;
  }
}

class ApiError extends Error {
  constructor(status, body = "") {
    super(`API error ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

function isRetryable(error) {
  if (error.name === "AbortError") return true; // timeout
  if (error instanceof ApiError && error.status >= 500) return true;
  if (error instanceof TypeError) return true; // network error
  return false;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Make available to non-module scripts (service worker, content script)
if (typeof globalThis !== "undefined") {
  globalThis.RealDealAPI = {
    analyzeProperty,
    apiPost,
    apiGet,
    checkHealth,
  };
}
