/**
 * RealDeal AI — Zillow Property Scraper
 *
 * Extracts property data from Zillow listing pages.
 * Uses DOM selectors with JSON-LD and __NEXT_DATA__ fallbacks.
 * Handles SPA navigation via MutationObserver.
 */

(function () {
  "use strict";

  const SELECTORS = {
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

  /**
   * Try multiple selectors, return first match's text content.
   */
  function queryText(selectors) {
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) {
        return el.textContent.trim();
      }
    }
    return null;
  }

  /**
   * Parse a price string like "$285,000" to a number.
   */
  function parsePrice(str) {
    if (!str) return null;
    const cleaned = str.replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned);
    return isNaN(val) ? null : val;
  }

  /**
   * Parse a numeric string like "1,450" to a number.
   */
  function parseNum(str) {
    if (!str) return null;
    const cleaned = str.replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned);
    return isNaN(val) ? null : val;
  }

  /**
   * Extract year built from the Facts & Features section.
   */
  function extractYearBuilt() {
    const factItems = document.querySelectorAll(
      ".ds-home-fact-list-container li, [data-testid='facts-list'] li"
    );
    for (const item of factItems) {
      const text = item.textContent;
      if (text && /year\s*built/i.test(text)) {
        const match = text.match(/(\d{4})/);
        if (match) return parseInt(match[1], 10);
      }
    }
    return null;
  }

  /**
   * Extract HOA fee from Facts & Features.
   */
  function extractHOA() {
    const factItems = document.querySelectorAll(
      ".ds-home-fact-list-container li, [data-testid='facts-list'] li"
    );
    for (const item of factItems) {
      const text = item.textContent;
      if (text && /hoa/i.test(text)) {
        if (/none/i.test(text)) return 0;
        const match = text.match(/\$([0-9,]+)/);
        if (match) return parseNum(match[1]);
      }
    }
    return null;
  }

  /**
   * Extract property type from Facts & Features.
   */
  function extractPropertyType() {
    const factItems = document.querySelectorAll(
      ".ds-home-fact-list-container li, [data-testid='facts-list'] li"
    );
    for (const item of factItems) {
      const text = item.textContent;
      if (text && /type/i.test(text) && !/heating|cooling/i.test(text)) {
        const type = text.replace(/type\s*:?\s*/i, "").trim();
        if (type) return type;
      }
    }
    return null;
  }

  /**
   * Extract zpid from the URL.
   */
  function extractZpid() {
    const match = window.location.pathname.match(/(\d+)_zpid/);
    return match ? match[1] : null;
  }

  /**
   * Try to get data from JSON-LD embedded in the page.
   */
  function extractFromJsonLd() {
    try {
      const scripts = document.querySelectorAll(
        'script[type="application/ld+json"]'
      );
      for (const script of scripts) {
        const data = JSON.parse(script.textContent);
        if (data["@type"] === "SingleFamilyResidence" || data["@type"] === "Product") {
          return {
            address: data.name || data.address?.streetAddress || null,
            price: data.offers?.price || null,
            sqft: data.floorSize?.value || null,
            beds: data.numberOfRooms || null,
          };
        }
      }
    } catch (e) {
      console.warn("[RealDeal] JSON-LD parse failed:", e);
    }
    return null;
  }

  /**
   * Try to get data from __NEXT_DATA__ hydration payload.
   */
  function extractFromNextData() {
    try {
      const el = document.getElementById("__NEXT_DATA__");
      if (!el) return null;
      const data = JSON.parse(el.textContent);
      const property =
        data?.props?.pageProps?.componentProps?.gdpClientCache;
      if (!property) return null;

      // The cache is keyed by zpid — grab the first entry
      const key = Object.keys(property)[0];
      if (!key) return null;
      const parsed = JSON.parse(property[key]);
      const details = parsed?.property;
      if (!details) return null;

      return {
        address: details.streetAddress,
        price: details.price,
        sqft: details.livingArea,
        beds: details.bedrooms,
        baths: details.bathrooms,
        yearBuilt: details.yearBuilt,
        zpid: details.zpid,
        zestimate: details.zestimate,
        propertyType: details.homeType,
        latitude: details.latitude,
        longitude: details.longitude,
        zipCode: details.zipcode,
      };
    } catch (e) {
      console.warn("[RealDeal] __NEXT_DATA__ parse failed:", e);
    }
    return null;
  }

  /**
   * Main extraction — combines DOM scraping with structured data fallbacks.
   */
  function extractPropertyData() {
    // Try structured sources first (more reliable)
    const nextData = extractFromNextData();
    const jsonLd = extractFromJsonLd();

    // DOM scraping
    const domData = {
      price: parsePrice(queryText(SELECTORS.price)),
      beds: parseNum(queryText(SELECTORS.beds)),
      baths: parseNum(queryText(SELECTORS.baths)),
      sqft: parseNum(queryText(SELECTORS.sqft)),
      address: queryText(SELECTORS.address),
      zestimate: parsePrice(queryText(SELECTORS.zestimate)),
      yearBuilt: extractYearBuilt(),
      hoa: extractHOA(),
      propertyType: extractPropertyType(),
      zpid: extractZpid(),
    };

    // Merge: prefer nextData > jsonLd > DOM, field by field
    const merged = { ...domData };
    const sources = [jsonLd, nextData]; // later sources take priority
    for (const source of sources) {
      if (!source) continue;
      for (const [key, val] of Object.entries(source)) {
        if (val != null && val !== "") {
          merged[key] = val;
        }
      }
    }

    return merged;
  }

  /**
   * Validate that we have minimum required fields.
   */
  function validate(data) {
    const required = ["price", "address"];
    const missing = required.filter((f) => !data[f]);
    if (missing.length > 0) {
      console.warn("[RealDeal] Missing required fields:", missing);
      return false;
    }
    if (data.price <= 0) {
      console.warn("[RealDeal] Invalid price:", data.price);
      return false;
    }
    return true;
  }

  /**
   * Send extracted data to the background service worker.
   */
  function sendToBackground(data) {
    chrome.runtime.sendMessage(
      { type: "PROPERTY_DATA", payload: data },
      (response) => {
        if (chrome.runtime.lastError) {
          console.warn("[RealDeal] Send failed:", chrome.runtime.lastError);
        }
      }
    );
  }

  /**
   * Run extraction with retries.
   */
  let extractionAttempts = 0;
  const MAX_ATTEMPTS = 3;
  const RETRY_DELAY = 500;

  function attemptExtraction() {
    const data = extractPropertyData();
    if (validate(data)) {
      console.log("[RealDeal] Property data extracted:", data);
      sendToBackground(data);
      return true;
    }

    extractionAttempts++;
    if (extractionAttempts < MAX_ATTEMPTS) {
      console.log(
        `[RealDeal] Retry ${extractionAttempts}/${MAX_ATTEMPTS} in ${RETRY_DELAY}ms`
      );
      setTimeout(attemptExtraction, RETRY_DELAY);
      return false;
    }

    console.warn("[RealDeal] Extraction failed after max attempts");
    // Send partial data anyway — backend can work with incomplete data
    sendToBackground(data);
    return false;
  }

  /**
   * Watch for SPA navigation (Zillow uses client-side routing).
   */
  function watchForNavigation() {
    let lastUrl = location.href;

    const observer = new MutationObserver(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        if (/\/homedetails\//.test(lastUrl)) {
          console.log("[RealDeal] SPA navigation detected, re-extracting...");
          extractionAttempts = 0;
          setTimeout(attemptExtraction, 1000); // Wait for new page content
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Initial extraction
  attemptExtraction();
  watchForNavigation();
})();
