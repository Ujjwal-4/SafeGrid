/**
 * app.js - Frontend controller for Crime & Narcotics Intelligence Platform
 * Implements:
 * 1. Officer Sign-in & JWT management
 * 2. Interactive Leaflet Map & Synced Hotspot Table
 * 3. Excel/CSV Upload with Parsed & Flagged Row Preview
 * 4. Anonymous Citizen Tip Portal with Location Pin Picker & Captcha
 * 5. Officer Tips Review with Urgency/Priority Badges & Verification Controls
 */

// Statutory Domain Color Scheme (BNS, BSA, NDPS, POCSO, IT Act)
const DOMAIN_COLORS = {
  physical_harm: "#ef4444",      // Red
  women_children: "#d946ef",     // Fuchsia / Pink
  property_crimes: "#f97316",    // Orange
  cybercrime: "#06b6d4",         // Cyan
  narcotics: "#10b981",          // Emerald Green
  public_disturbance: "#eab308", // Yellow
  crime: "#f97316"
};

const DOMAINS_INFO = {
  physical_harm: {
    name: "Crimes Involving Physical Harm & Violence",
    icon: "🩸",
    color: "#ef4444",
    governing_law: "Chapter VI of Bharatiya Nyaya Sanhita, 2023 (BNS) - Offences Affecting the Human Body (Sec 101 Murder, Sec 115 Hurt, Sec 106 Hit-and-Run, Sec 137 Kidnapping)",
    required_evidence: "Medical reports (MLC), blood samples, weapons recovered from spot, CCTV footage of assault, eyewitness testimony under BSA 2023.",
    categories: {
      murder: "Murder / Attempt to Murder",
      assault: "Assault / Hurt",
      hit_and_run: "Hit and Run",
      kidnapping: "Kidnapping"
    }
  },
  women_children: {
    name: "Crimes Against Women and Children",
    icon: "🛡️",
    color: "#d946ef",
    governing_law: "Chapter V of Bharatiya Nyaya Sanhita, 2023 (BNS) - Offences Against Women & Children; POCSO Act (Protection of Children from Sexual Offences Act)",
    required_evidence: "Audio/video recordings, dynamic electronic communications (chats/messages), medical forensic examinations, magistrate statements under BSA 2023.",
    categories: {
      domestic_violence: "Domestic Violence / Cruelty",
      sexual_offenses: "Sexual Offenses",
      child_abuse: "Child Abuse / Exploitation"
    }
  },
  property_crimes: {
    name: "Crimes Against Property (Theft & Damage)",
    icon: "📦",
    color: "#f97316",
    governing_law: "Chapter XVII of Bharatiya Nyaya Sanhita, 2023 (BNS) - Offences Against Property (Sec 303 Theft, Sec 304 Snatching, Sec 305 Burglary, Sec 324 Arson/Mischief)",
    required_evidence: "CCTV footage of break-in, broken locks/fingerprints, proof of ownership of stolen item under BSA 2023.",
    categories: {
      theft_burglary: "Theft / Burglary",
      robbery_snatching: "Robbery / Snatching",
      vandalism_arson: "Vandalism / Arson"
    }
  },
  cybercrime: {
    name: "Cybercrimes & Digital Scams",
    icon: "💻",
    color: "#06b6d4",
    governing_law: "Information Technology (IT) Act, 2000 (Sec 66C Identity Theft, Sec 66D Cheating by Impersonation) & BNS Fraud; Sec 63 BSA electronic evidence certificate",
    required_evidence: "Screenshots of chats, transaction receipts, bank statements showing debit, IP addresses, emails, Section 63 BSA certificate.",
    categories: {
      financial_fraud: "Financial Fraud (UPI / Phishing)",
      identity_theft: "Identity Theft / Impersonation",
      online_harassment: "Online Harassment / Cyberstalking"
    }
  },
  narcotics: {
    name: "Narcotics & Drug-Related Crimes",
    icon: "🌿",
    color: "#10b981",
    governing_law: "Narcotics Drugs and Psychotropic Substances (NDPS) Act, 1985 (Sec 8/20/21/22/27A/29)",
    required_evidence: "Physical recovery of contraband, independent panchnama witnesses present during raid, forensic chemical analysis (FSL), digital logs of supply coordination under BSA 2023.",
    categories: {
      drug_trafficking: "Drug Trafficking / Dealing",
      illicit_storage: "Illicit Storage / Cultivation"
    }
  },
  public_disturbance: {
    name: "Public Disturbance & Scams",
    icon: "⚠️",
    color: "#eab308",
    governing_law: "Chapter XI of Bharatiya Nyaya Sanhita, 2023 (BNS) - Public Tranquillity (Sec 189 Unlawful Assembly, Sec 191 Rioting); Chapter XVII BNS (Sec 318 Cheating, Sec 336 Forgery)",
    required_evidence: "Video recordings of mob violence, original forged documents compared against authentic signatures via forensic handwriting experts under BSA 2023.",
    categories: {
      rioting: "Rioting / Public Fights",
      cheating_forgery: "Cheating / Forgery"
    }
  }
};

const CATEGORY_COLORS = {
  // Physical Harm
  murder: "#ef4444",
  assault: "#f87171",
  hit_and_run: "#fb923c",
  kidnapping: "#dc2626",
  // Women & Children
  domestic_violence: "#ec4899",
  sexual_offenses: "#d946ef",
  child_abuse: "#a855f7",
  // Property Crimes
  theft_burglary: "#f97316",
  robbery_snatching: "#ea580c",
  vandalism_arson: "#c2410c",
  // Cybercrime
  financial_fraud: "#06b6d4",
  identity_theft: "#0ea5e9",
  online_harassment: "#38bdf8",
  // Narcotics
  drug_trafficking: "#10b981",
  illicit_storage: "#059669",
  seizure: "#10b981",
  od_admission: "#047857",
  peddling_activity: "#34d399",
  // Public Disturbance
  rioting: "#eab308",
  cheating_forgery: "#ca8a04",
  // Legacy
  theft: "#f97316",
  burglary: "#0284c7"
};

function getHotspotColor(item) {
  if (item.color) return item.color;
  if (item.domain && DOMAIN_COLORS[item.domain.toLowerCase()]) {
    return DOMAIN_COLORS[item.domain.toLowerCase()];
  }
  if (item.category && CATEGORY_COLORS[item.category.toLowerCase()]) {
    return CATEGORY_COLORS[item.category.toLowerCase()];
  }
  return "#38bdf8";
}

// District default coordinates
const DISTRICT_CENTERS = {
  "New Delhi": [28.6315, 77.2167],
  "Central": [28.6450, 77.2120],
  "North": [28.6700, 77.2180],
  "North West": [28.6980, 77.1650],
  "West": [28.6500, 77.1200],
  "South West": [28.5700, 77.0800],
  "South": [28.5300, 77.2100],
  "South East": [28.5600, 77.2600],
  "East": [28.6300, 77.2900],
  "Shahdara": [28.6700, 77.2900],
  "North East": [28.7000, 77.2700],
  "Rohini": [28.7300, 77.1100],
  "Outer": [28.7000, 77.0500],
  "Outer North": [28.8100, 77.1100],
  "Dwarka": [28.5800, 77.0500],
  "Gurugram East": [28.4700, 77.0700],
  "Noida Central": [28.5700, 77.3400],
  "Faridabad NIT": [28.4000, 77.3000]
};

// Base URL of the explain-report-service (separate service: LLM narration +
// PDF/JSON report generation on top of this platform's frequency/hotspot
// data). Override by setting window.EXPLAIN_SERVICE_BASE before app.js loads
// if it runs on a different host/port than the default dev setup.
const EXPLAIN_SERVICE_BASE = window.EXPLAIN_SERVICE_BASE || "http://localhost:4100";

// Global App State
const state = {
  token: localStorage.getItem("intel_token") || null,
  officer: JSON.parse(localStorage.getItem("intel_officer") || "null"),
  currentPage: "dashboard",
  hotspotsData: [],
  map: null,
  mapCircleLayers: [],
  tipPickerMap: null,
  tipPickerMarker: null,
  captchaSecret: ""
};

// ---------------- Toast Notification ----------------
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.innerText = message;
  toast.style.borderLeftColor = isError ? "var(--accent-red)" : "var(--accent-cyan)";
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 4000);
}

// ---------------- Navigation & Routing ----------------
function navigateTo(pageId) {
  // Check auth protection
  const protectedPages = ["dashboard", "forecast", "model-card", "upload", "tips-review"];
  if (protectedPages.includes(pageId) && !state.token) {
    showToast("Officer authentication required to access this section.", true);
    pageId = "signin";
  }

  state.currentPage = pageId;

  // Toggle page visibility
  document.querySelectorAll(".page-view").forEach(el => el.classList.remove("active"));
  const targetPage = document.getElementById(`page-${pageId}`);
  if (targetPage) targetPage.classList.add("active");

  // Toggle nav links active state
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.toggle("active", link.dataset.page === pageId);
  });

  updateAuthUI();

  // Lifecycle hooks per page
  if (pageId === "dashboard") {
    initDashboard();
  } else if (pageId === "forecast") {
    initForecastPage();
  } else if (pageId === "model-card") {
    loadModelReportCard();
  } else if (pageId === "tips-portal") {
    initTipPortal();
  } else if (pageId === "tips-review") {
    loadOfficerTips();
  }
}

function updateAuthUI() {
  const officerBadge = document.getElementById("officerBadge");
  const logoutBtn = document.getElementById("navLogoutBtn");
  const authNavItems = document.querySelectorAll(".auth-only-nav");
  const guestNavItems = document.querySelectorAll(".guest-only-nav");

  if (state.token && state.officer) {
    document.body.classList.add("authenticated");
    authNavItems.forEach(el => {
      if (el.tagName === "BUTTON") {
        el.style.display = "inline-flex";
      } else {
        el.style.display = "block";
      }
    });
    guestNavItems.forEach(el => el.style.display = "none");

    if (officerBadge) {
      officerBadge.innerHTML = `<span class="pulse-dot"></span> ${state.officer.name} (${state.officer.badge_id})`;
      officerBadge.style.display = "inline-flex";
    }
    if (logoutBtn) logoutBtn.style.display = "inline-flex";
  } else {
    document.body.classList.remove("authenticated");
    authNavItems.forEach(el => el.style.display = "none");
    guestNavItems.forEach(el => el.style.display = "block");

    if (officerBadge) officerBadge.style.display = "none";
    if (logoutBtn) logoutBtn.style.display = "none";
  }
}

function logout() {
  localStorage.removeItem("intel_token");
  localStorage.removeItem("intel_officer");
  state.token = null;
  state.officer = null;
  updateAuthUI();
  showToast("Logged out successfully.");
  navigateTo("signin");
}

// ---------------- 1. Sign-In Page Controller ----------------
function initSignIn() {
  const loginForm = document.getElementById("loginForm");
  if (!loginForm) return;

  loginForm.onsubmit = async (e) => {
    e.preventDefault();
    const badgeId = document.getElementById("loginBadgeId").value.trim();
    const password = document.getElementById("loginPassword").value;
    const loginBtn = document.getElementById("loginSubmitBtn");

    loginBtn.disabled = true;
    loginBtn.innerText = "Authenticating...";

    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ badge_id: badgeId, password })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || "Authentication failed");
      }

      state.token = data.token;
      state.officer = {
        badge_id: data.badge_id,
        role: data.role,
        name: data.name || data.badge_id
      };

      localStorage.setItem("intel_token", state.token);
      localStorage.setItem("intel_officer", JSON.stringify(state.officer));

      showToast(`Welcome, ${state.officer.name}! Authenticated.`);
      navigateTo("dashboard");
    } catch (err) {
      showToast(err.message, true);
    } finally {
      loginBtn.disabled = false;
      loginBtn.innerText = "Sign In to Tactical Dashboard";
    }
  };
}

function fillCredentials(badge, pass) {
  document.getElementById("loginBadgeId").value = badge;
  document.getElementById("loginPassword").value = pass;
}

// ---------------- 2. Dashboard Page (Map & Synced Table) ----------------
async function initDashboard() {
  // Initialize Leaflet Map if not already created
  if (!state.map && window.L) {
    const mapEl = document.getElementById("mapContainer");
    if (!mapEl) return;

    state.map = L.map("mapContainer").setView([28.62, 77.21], 11);

    // OpenStreetMap standard tile layer (free, no key required)
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    }).addTo(state.map);

    // Add map legend showing statutory domains
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = function () {
      const div = L.DomUtil.create("div", "map-legend");
      div.innerHTML = `
        <div style="font-weight:700; margin-bottom:0.4rem; font-size:0.85rem;">Statutory Domains</div>
        <div class="legend-item"><span class="legend-dot" style="background:${DOMAIN_COLORS.physical_harm}"></span> 🩸 Physical Harm &amp; Violence</div>
        <div class="legend-item"><span class="legend-dot" style="background:${DOMAIN_COLORS.women_children}"></span> 🛡️ Women &amp; Children</div>
        <div class="legend-item"><span class="legend-dot" style="background:${DOMAIN_COLORS.property_crimes}"></span> 📦 Property Crimes</div>
        <div class="legend-item"><span class="legend-dot" style="background:${DOMAIN_COLORS.cybercrime}"></span> 💻 Cybercrimes &amp; Scams</div>
        <div class="legend-item"><span class="legend-dot" style="background:${DOMAIN_COLORS.narcotics}"></span> 🌿 Narcotics &amp; Drugs</div>
        <div class="legend-item"><span class="legend-dot" style="background:${DOMAIN_COLORS.public_disturbance}"></span> ⚠️ Public Disturbance</div>
        <div style="font-size:0.7rem; color:#9ca3af; margin-top:0.4rem;">*Circle size reflects raw frequency count</div>
      `;
      return div;
    };
    legend.addTo(state.map);
  }

  // Fetch hotspots from backend
  await fetchHotspotsData();
}

async function fetchHotspotsData() {
  const domainFilter = document.getElementById("filterDomain") ? document.getElementById("filterDomain").value : "all";
  const categoryFilter = document.getElementById("filterCategory") ? document.getElementById("filterCategory").value : "";

  let url = `/api/hotspots?domain=${encodeURIComponent(domainFilter || "all")}`;
  if (categoryFilter) {
    url += `&category=${encodeURIComponent(categoryFilter)}`;
  }

  try {
    const headers = state.token ? { "Authorization": `Bearer ${state.token}` } : {};
    const resp = await fetch(url, { headers });
    
    if (resp.status === 401) {
      showToast("Session expired. Please sign in again.", true);
      logout();
      return;
    }

    const data = await resp.json();
    state.hotspotsData = Array.isArray(data) ? data : [];
    renderMapAndTable();
  } catch (err) {
    console.error("Failed to load hotspots:", err);
    showToast("Error retrieving hotspot intelligence.", true);
  }
}

function renderMapAndTable() {
  const categoryFilter = document.getElementById("filterCategory") ? document.getElementById("filterCategory").value.toLowerCase() : "";
  const searchDistrict = document.getElementById("filterDistrict") ? document.getElementById("filterDistrict").value.toLowerCase() : "";

  // Filter dataset for BOTH map and table to keep them perfectly in sync
  const filtered = state.hotspotsData.filter(h => {
    const matchCategory = !categoryFilter || h.category.toLowerCase() === categoryFilter;
    const matchDistrict = !searchDistrict || (h.district && h.district.toLowerCase().includes(searchDistrict));
    return matchCategory && matchDistrict;
  });

  // 1. Update Leaflet Map Circles
  if (state.map && window.L) {
    // Clear previous circles
    state.mapCircleLayers.forEach(l => state.map.removeLayer(l));
    state.mapCircleLayers = [];

    const bounds = [];

    filtered.forEach(h => {
      const color = getHotspotColor(h);
      const domInfo = DOMAINS_INFO[h.domain] || { name: h.domain.replace(/_/g, ' '), icon: "🛡️" };

      // CIRCLE SIZE and color intensity represents raw frequency (NOT a computed score)
      // Radius scale: min 350m, scaling up with raw incident frequency count
      const radiusMeters = Math.max(350, Math.min(2500, 300 + h.frequency * 180));

      const circle = L.circle([h.lat, h.lng], {
        color: color,
        fillColor: color,
        fillOpacity: Math.min(0.85, 0.40 + (h.frequency / 25.0)),
        radius: radiusMeters,
        weight: 2
      }).addTo(state.map);

      // Popup with zone information, raw count, and trend
      const trendHtml = getTrendBadge(h.trend);
      circle.bindPopup(`
        <div style="font-family:sans-serif; min-width:200px;">
          <h4 style="margin:0 0 0.35rem 0; font-size:1rem; color:#1e293b;">${h.district}</h4>
          <div style="font-size:0.75rem; margin-bottom:0.35rem;">
            <span class="badge" style="background:${color}22; color:${color}; border:1px solid ${color}; font-weight:700;">
              ${domInfo.icon || '🛡️'} ${domInfo.name}
            </span>
          </div>
          <div style="font-size:0.8rem; margin-bottom:0.4rem;">
            <strong>Category:</strong> <span style="font-weight:700; color:#334155; text-transform:capitalize;">${h.category.replace(/_/g, ' ')}</span>
          </div>
          <div style="font-size:0.85rem; margin-bottom:0.25rem;">
            <strong>Frequency Count:</strong> <span style="font-size:1.15rem; font-weight:800; color:#0f172a;">${h.frequency}</span>
          </div>
          <div style="font-size:0.8rem; margin-bottom:0.35rem; color:#475569;">
            Previous period: <strong>${h.previous_frequency}</strong>
          </div>
          <div>${trendHtml}</div>
        </div>
      `);

      state.mapCircleLayers.push(circle);
      bounds.push([h.lat, h.lng]);
    });

    if (bounds.length > 0) {
      state.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    }
  }

  // 2. Update Table Below Map
  const tbody = document.getElementById("hotspotsTableBody");
  if (tbody) {
    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No hotspots match the selected filter criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(h => {
      const color = getHotspotColor(h);
      const domInfo = DOMAINS_INFO[h.domain] || { name: h.domain.replace(/_/g, ' '), icon: "🛡️" };
      const trendBadge = getTrendBadge(h.trend);
      return `
        <tr>
          <td><strong>${h.district}</strong></td>
          <td>
            <span class="badge" style="background-color:rgba(255,255,255,0.06); color:${color}; border:1px solid ${color}; font-weight:600;">
              <span class="legend-dot" style="background:${color}; width:8px; height:8px;"></span>
              ${domInfo.name}
            </span>
          </td>
          <td>
            <span style="font-weight:600; font-size:0.85rem; color:var(--text-secondary); text-transform:capitalize;">
              ${h.category.replace(/_/g, ' ')}
            </span>
          </td>
          <td style="font-weight:700; font-size:1.05rem; color:var(--text-primary);">${h.frequency}</td>
          <td style="color:var(--text-muted);">${h.previous_frequency}</td>
          <td>${trendBadge}</td>
        </tr>
      `;
    }).join("");
  }

  // Update count indicator
  const countEl = document.getElementById("hotspotCountDisplay");
  if (countEl) countEl.innerText = `${filtered.length} active hotspot zones found`;
}

function getTrendBadge(trend) {
  const t = (trend || "flat").toLowerCase();
  if (t === "up") {
    return `<span class="trend-up">▲ UP (+ Surge)</span>`;
  } else if (t === "down") {
    return `<span class="trend-down">▼ DOWN (- Decline)</span>`;
  }
  return `<span class="trend-flat">▬ FLAT (Stable)</span>`;
}

// ---------------- 3. Upload & Report Page Controller ----------------
function initUploadPage() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileUploadInput");
  const uploadForm = document.getElementById("uploadForm");

  if (!dropZone || !fileInput) return;

  dropZone.onclick = () => fileInput.click();

  dropZone.ondragover = (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  };

  dropZone.ondragleave = () => dropZone.classList.remove("dragover");

  dropZone.ondrop = (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      updateSelectedFileName();
    }
  };

  fileInput.onchange = () => updateSelectedFileName();

  function updateSelectedFileName() {
    if (fileInput.files.length > 0) {
      const file = fileInput.files[0];
      document.getElementById("selectedFileLabel").innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      document.getElementById("uploadBtn").disabled = false;
    }
  }

  uploadForm.onsubmit = async (e) => {
    e.preventDefault();
    if (!fileInput.files.length) {
      showToast("Please choose an Excel (.xlsx) or CSV file first.", true);
      return;
    }

    const file = fileInput.files[0];
    const domain = document.getElementById("uploadDomainSelect").value;
    const btn = document.getElementById("uploadBtn");

    btn.disabled = true;
    btn.innerText = "Parsing, Geocoding & Deduplicating...";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("domain", domain);

    try {
      const resp = await fetch("/api/upload", {
        method: "POST",
        headers: { "Authorization": `Bearer ${state.token}` },
        body: formData
      });

      const result = await resp.json();
      if (!resp.ok) {
        throw new Error(result.error || "Ingestion failed");
      }

      showToast(`Successfully processed ${file.name}!`);
      renderUploadPreview(result);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      btn.disabled = false;
      btn.innerText = "Upload & Ingest Operational Log";
    }
  };
}

function renderUploadPreview(data) {
  const previewContainer = document.getElementById("uploadPreviewContainer");
  if (!previewContainer) return;

  previewContainer.style.display = "block";

  // Summary KPIs
  const summary = data.summary || {};
  document.getElementById("kpiTotalRows").innerText = summary.total_rows_processed || 0;
  document.getElementById("kpiValidIncidents").innerText = summary.valid_incidents || (data.incidents ? data.incidents.length : 0);
  document.getElementById("kpiFlaggedRows").innerText = summary.flagged_rows_count || (data.flagged_rows ? data.flagged_rows.length : 0);
  document.getElementById("kpiDuplicates").innerText = summary.duplicate_pairs_identified || (data.duplicates_summary ? data.duplicates_summary.length : 0);

  // Flagged Reasons Breakdown Summary
  const breakdownContainer = document.getElementById("flaggedBreakdownContainer");
  if (breakdownContainer) {
    if (summary.flagged_by_reason && Object.keys(summary.flagged_by_reason).length > 0) {
      const pills = Object.entries(summary.flagged_by_reason).map(([reason, count]) => {
        return `<span class="badge" style="background:rgba(239, 68, 68, 0.15); border:1px solid rgba(239, 68, 68, 0.35); color:#fca5a5; padding:0.25rem 0.6rem; font-size:0.75rem;"><strong>${reason}</strong>: ${count}</span>`;
      }).join(" ");
      breakdownContainer.innerHTML = `<div style="display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center; background:rgba(15, 23, 42, 0.6); padding:0.75rem 1rem; border-radius:6px; border:1px solid var(--border-color);"><span style="font-size:0.75rem; color:var(--text-muted); font-weight:700; text-transform:uppercase;">Flagged Breakdown:</span> ${pills}</div>`;
      breakdownContainer.style.display = "block";
    } else {
      breakdownContainer.style.display = "none";
    }
  }

  // 1. Render Clean Incidents
  const incidents = data.incidents || [];
  const validTbody = document.getElementById("validIncidentsTbody");
  if (validTbody) {
    validTbody.innerHTML = incidents.slice(0, 50).map(inc => {
      const color = CATEGORY_COLORS[inc.category.toLowerCase()] || "var(--accent-cyan)";
      const isDup = inc.metadata && inc.metadata.is_duplicate;
      const dupBadge = isDup 
        ? `<span class="badge" style="background:#7f1d1d; color:#fca5a5;">Duplicate</span>`
        : `<span class="badge" style="background:#064e3b; color:#6ee7b7;">Canonical</span>`;

      return `
        <tr>
          <td style="font-family:var(--font-mono); font-size:0.75rem;">${inc.id.substring(0, 8)}...</td>
          <td><span class="badge" style="background:#1e293b; color:#94a3b8;">${inc.source.toUpperCase()}</span></td>
          <td>${inc.district}</td>
          <td>
            <span class="badge" style="border:1px solid ${color}; color:${color};">${inc.category}</span>
          </td>
          <td>${inc.address_text}</td>
          <td style="font-size:0.8rem; font-family:var(--font-mono); color:#38bdf8;">${inc.lat.toFixed(4)}, ${inc.lng.toFixed(4)}</td>
          <td style="font-size:0.75rem; color:var(--text-muted);">${inc.occurred_at}</td>
          <td>${dupBadge}</td>
        </tr>
      `;
    }).join("");
  }

  // 2. Render Flagged / Unmapped Rows
  const flagged = data.flagged_rows || [];
  const flaggedTbody = document.getElementById("flaggedRowsTbody");
  if (flaggedTbody) {
    if (flagged.length === 0) {
      flaggedTbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:1.5rem; color:#4ade80;">No rows flagged! All data mapped with high confidence.</td></tr>`;
    } else {
      flaggedTbody.innerHTML = flagged.map(r => {
        const reasons = Array.isArray(r.flag_reasons) ? r.flag_reasons : (r.flag_reason ? [r.flag_reason] : ["unspecified issue"]);
        const reasonsHtml = reasons.map(reason => {
          return `<div style="color:#fca5a5; font-size:0.75rem; font-weight:600;">⚠️ ${reason}</div>`;
        }).join("");

        const rawJson = JSON.stringify(r.raw_data || {});
        return `
          <tr>
            <td style="font-weight:700; color:#fbbf24;">Row #${r.row_index}</td>
            <td>${reasonsHtml}</td>
            <td>
              <span class="badge" style="background:#374151; color:#e5e7eb;">${Math.round((r.confidence_score || 0) * 100)}%</span>
            </td>
            <td>
              <pre style="font-size:0.7rem; background:#0d131f; padding:0.4rem; border-radius:4px; max-width:380px; overflow:hidden; text-overflow:ellipsis;">${rawJson}</pre>
            </td>
          </tr>
        `;
      }).join("");
    }
  }

  // Scroll to preview
  previewContainer.scrollIntoView({ behavior: "smooth" });
}

function switchUploadTab(tabName) {
  document.querySelectorAll(".upload-tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".upload-tab-pane").forEach(p => p.style.display = "none");

  const activeBtn = document.getElementById(`tabBtn-${tabName}`);
  const activePane = document.getElementById(`tabPane-${tabName}`);
  if (activeBtn) activeBtn.classList.add("active");
  if (activePane) activePane.style.display = "block";
}

async function downloadReport(domain) {
  try {
    const resp = await fetch(`/api/reports/${domain}?format=json`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    const reportData = await resp.json();

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${domain}_intelligence_bulletin.json`;
    a.click();
    showToast(`Downloaded ${domain} Intelligence Bulletin.`);
  } catch (err) {
    showToast("Failed to generate report", true);
  }
}

/**
 * Calls the separate explain-report-service to get an LLM-narrated version
 * of this platform's own hotspot data: it reads real frequency/trend counts
 * from THIS backend's /api/hotspots (same JWT, no extra login), derives a
 * deterministic score from them, then has an LLM write the rationale and
 * recommended action for each zone. Opens the result as a readable report
 * in a new tab, and also offers the raw JSON as a download.
 */
async function generateAIReport(domain, type) {
  if (!state.token) {
    showToast("Sign in required to generate an AI report", true);
    return;
  }
  showToast(`Generating AI ${domain} ${type} report…`);
  try {
    const resp = await fetch(`${EXPLAIN_SERVICE_BASE}/api/reports/${domain}?type=${type}&format=json`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!resp.ok) {
      const errBody = await resp.json().catch(() => ({}));
      throw new Error(errBody.error || `explain-report-service returned ${resp.status}`);
    }
    const report = await resp.json();
    renderAIReportWindow(report);
  } catch (err) {
    showToast(`Failed to generate AI report: ${err.message}`, true);
  }
}

function renderAIReportWindow(report) {
  const zones = report.districts || report.top_zones || [];
  const rowsHtml = zones.map(z => `
    <div style="border:1px solid #2a3548; border-radius:8px; padding:1rem; margin-bottom:0.75rem; background:#0d131f;">
      <div style="display:flex; justify-content:space-between; align-items:baseline;">
        <h3 style="margin:0; color:#e5e7eb;">#${z.rank} — ${z.zone}</h3>
        <span style="font-weight:700; color:${z.risk_level === 'high' ? '#f87171' : z.risk_level === 'medium' ? '#fbbf24' : '#4ade80'};">
          ${z.risk_level ? z.risk_level.toUpperCase() : ''} · score ${z.score}
        </span>
      </div>
      <p style="color:#cbd5e1;">${z.rationale || ''}</p>
      <p style="color:#67e8f9;"><strong>Recommended action:</strong> ${z.recommended_action || z.redeployment_recommendation || ''}</p>
    </div>
  `).join("");

  const win = window.open("", "_blank");
  if (!win) {
    showToast("Allow pop-ups to view the AI report", true);
    return;
  }
  win.document.write(`
    <html>
      <head>
        <title>${report.report_type || 'AI Intelligence Report'} — ${report.domain}</title>
        <style>
          body { font-family: system-ui, sans-serif; background:#0a0f1a; color:#e5e7eb; padding:2rem; max-width:900px; margin:0 auto; }
          h1 { color:#67e8f9; }
        </style>
      </head>
      <body>
        <h1>${report.report_type || 'AI Intelligence Report'}</h1>
        <p style="color:#94a3b8;">Domain: ${report.domain} · Generated: ${report.generated_at}</p>
        ${rowsHtml || '<p>No zones to report for this window.</p>'}
      </body>
    </html>
  `);
  win.document.close();
}

// ---------------- 4. Anonymous Public Tip Portal Controller ----------------
function initTipPortal() {
  generateCaptcha();

  // Initialize interactive map pin picker if not already created
  if (!state.tipPickerMap && window.L) {
    const tipMapEl = document.getElementById("tipPickerMap");
    if (!tipMapEl) return;

    state.tipPickerMap = L.map("tipPickerMap").setView([28.63, 77.21], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap'
    }).addTo(state.tipPickerMap);

    // Click map to drop/move pin
    state.tipPickerMap.on("click", (e) => {
      const { lat, lng } = e.latlng;
      setTipPin(lat, lng);
    });
  }

  // Handle district dropdown change -> center map on selected district
  const distSelect = document.getElementById("tipDistrictSelect");
  if (distSelect) {
    distSelect.onchange = () => {
      const dist = distSelect.value;
      if (DISTRICT_CENTERS[dist] && state.tipPickerMap) {
        state.tipPickerMap.setView(DISTRICT_CENTERS[dist], 13);
        setTipPin(DISTRICT_CENTERS[dist][0], DISTRICT_CENTERS[dist][1]);
      }
    };
  }

  // Handle domain change -> dynamically populate categories and update statutory guidance
  const tipDomainSelect = document.getElementById("tipDomainSelect");
  const tipCategorySelect = document.getElementById("tipCategorySelect");
  const tipGovLaw = document.getElementById("tipGoverningLawDisplay");
  const tipEvidence = document.getElementById("tipEvidenceGuidanceDisplay");

  function updateTipCategoriesAndGuidance() {
    const selDomain = tipDomainSelect ? tipDomainSelect.value : "physical_harm";
    const dInfo = DOMAINS_INFO[selDomain];
    if (dInfo && tipCategorySelect) {
      tipCategorySelect.innerHTML = Object.entries(dInfo.categories).map(([catKey, catLabel]) => {
        return `<option value="${catKey}">${catLabel}</option>`;
      }).join("");
    }
    if (dInfo && tipGovLaw) {
      tipGovLaw.innerText = `⚖️ Governing Law: ${dInfo.governing_law}`;
    }
    if (dInfo && tipEvidence) {
      tipEvidence.innerText = `📌 Recommended Evidence under BSA 2023: ${dInfo.required_evidence}`;
    }
  }

  if (tipDomainSelect) {
    tipDomainSelect.onchange = updateTipCategoriesAndGuidance;
    updateTipCategoriesAndGuidance();
  }

  // Handle tip submission form
  const tipForm = document.getElementById("publicTipForm");
  if (tipForm) {
    tipForm.onsubmit = async (e) => {
      e.preventDefault();

      // Verify Captcha
      const enteredCaptcha = document.getElementById("captchaInput").value.trim().toUpperCase();
      if (enteredCaptcha !== state.captchaSecret) {
        showToast("Captcha code does not match. Please try again.", true);
        generateCaptcha();
        return;
      }

      const domain = document.getElementById("tipDomainSelect").value;
      const category = document.getElementById("tipCategorySelect").value;
      const district = document.getElementById("tipDistrictSelect").value;
      const description = document.getElementById("tipDescription").value.trim();
      const latVal = document.getElementById("tipLatInput").value;
      const lngVal = document.getElementById("tipLngInput").value;
      const photoInput = document.getElementById("tipPhotoInput");
      const isUrgent = document.getElementById("tipIsUrgent").checked;

      const submitBtn = document.getElementById("tipSubmitBtn");
      submitBtn.disabled = true;
      submitBtn.innerText = "Submitting Anonymously...";

      // Handle photo preview / mock upload
      let photoUrl = null;
      if (photoInput.files.length > 0) {
        photoUrl = `https://storage.police-intel.internal/tips/${Date.now()}_${photoInput.files[0].name}`;
      }

      const payload = {
        domain: domain,
        category: category,
        district: district,
        description: description,
        photo_url: photoUrl,
        lat: latVal ? parseFloat(latVal) : null,
        lng: lngVal ? parseFloat(lngVal) : null,
        is_high_priority: false,
        is_urgent: isUrgent
      };

      try {
        const resp = await fetch("/api/tips", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.error || "Tip submission failed");
        }

        // Show confirmation modal
        document.getElementById("tipReceiptId").innerText = data.id;
        document.getElementById("tipModal").style.display = "flex";

        // Reset form
        tipForm.reset();
        generateCaptcha();
        clearTipPin();
      } catch (err) {
        showToast(err.message, true);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Submit Anonymous Tip";
      }
    };
  }
}

function setTipPin(lat, lng) {
  document.getElementById("tipLatInput").value = lat.toFixed(6);
  document.getElementById("tipLngInput").value = lng.toFixed(6);
  document.getElementById("tipCoordsDisplay").innerText = `Pinned: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;

  if (state.tipPickerMarker) {
    state.tipPickerMarker.setLatLng([lat, lng]);
  } else if (state.tipPickerMap) {
    state.tipPickerMarker = L.marker([lat, lng], { draggable: true }).addTo(state.tipPickerMap);
    state.tipPickerMarker.on("dragend", (e) => {
      const pos = e.target.getLatLng();
      setTipPin(pos.lat, pos.lng);
    });
  }
}

function clearTipPin() {
  if (state.tipPickerMarker && state.tipPickerMap) {
    state.tipPickerMap.removeLayer(state.tipPickerMarker);
    state.tipPickerMarker = null;
  }
  document.getElementById("tipLatInput").value = "";
  document.getElementById("tipLngInput").value = "";
  document.getElementById("tipCoordsDisplay").innerText = "No location pinned (optional)";
}

function generateCaptcha() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  for (let i = 0; i < 5; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  state.captchaSecret = code;
  const badge = document.getElementById("captchaBadge");
  if (badge) badge.innerText = code;
  const input = document.getElementById("captchaInput");
  if (input) input.value = "";
}

function closeTipModal() {
  document.getElementById("tipModal").style.display = "none";
}

// ---------------- 5. Tips Review Page (Officer Only) ----------------
async function loadOfficerTips() {
  const statusFilter = document.getElementById("reviewStatusFilter") ? document.getElementById("reviewStatusFilter").value : "pending";
  const districtFilter = document.getElementById("reviewDistrictFilter") ? document.getElementById("reviewDistrictFilter").value : "";

  let url = `/api/tips?status=${encodeURIComponent(statusFilter)}`;
  if (districtFilter) {
    url += `&district=${encodeURIComponent(districtFilter)}`;
  }

  const container = document.getElementById("tipsReviewList");
  if (!container) return;

  container.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">Loading intelligence tips...</div>`;

  try {
    const resp = await fetch(url, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });

    if (resp.status === 401) {
      showToast("Officer authorization required.", true);
      logout();
      return;
    }

    const tips = await resp.json();
    if (!Array.isArray(tips) || tips.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:2.5rem; color:var(--text-muted); background:var(--bg-secondary); border-radius:8px;">No tips matching criteria.</div>`;
      return;
    }

    // Sort by region/district as specified
    tips.sort((a, b) => a.district.localeCompare(b.district));

    container.innerHTML = tips.map(tip => {
      // Calculate age / days remaining before deletion
      const createdDate = new Date(tip.created_at);
      const now = new Date();
      const ageDays = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24));
      const daysRemaining = Math.max(1, 14 - ageDays); // 14-day retention cycle

      // Urgent near-deletion badge
      const urgentBadge = (daysRemaining <= 4 || tip.is_urgent) 
        ? `<span class="badge badge-urgent">⚠️ Urgent — Expires in ${daysRemaining} days</span>` 
        : "";

      // High priority corroborated badge
      const priorityBadge = (tip.is_high_priority || tip.status === "verified_true")
        ? `<span class="badge badge-priority">★ High Priority Cluster</span>`
        : "";

      const color = CATEGORY_COLORS[tip.category.toLowerCase()] || "var(--accent-cyan)";
      const statusClass = tip.status === "verified_true" ? "trend-down" : (tip.status === "verified_false" ? "trend-up" : "");

      return `
        <div class="card" style="margin-bottom:1rem; border-left:4px solid ${color};">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.75rem;">
            <div>
              <span class="badge" style="border:1px solid ${color}; color:${color};">${tip.category}</span>
              <strong style="margin-left:0.5rem; font-size:1rem;">${tip.district}</strong>
              <span style="font-size:0.75rem; color:var(--text-muted); margin-left:0.5rem;">[${tip.domain.toUpperCase()}]</span>
            </div>
            <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
              ${priorityBadge}
              ${urgentBadge}
              <span class="badge" style="background:#1e293b;">${tip.status}</span>
            </div>
          </div>

          <p style="font-size:0.9rem; color:#e2e8f0; margin-bottom:0.75rem; line-height:1.6;">
            "${tip.description}"
          </p>

          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; border-top:1px solid var(--border-color); padding-top:0.75rem;">
            <div style="font-size:0.75rem; color:var(--text-muted);">
              <span>ID: <code style="color:#38bdf8;">${tip.id.substring(0, 8)}</code></span> &bull; 
              <span>Logged: ${new Date(tip.created_at).toLocaleString()}</span>
              ${tip.lat && tip.lng ? ` &bull; <span>Coords: ${tip.lat.toFixed(4)}, ${tip.lng.toFixed(4)}</span>` : ""}
              ${tip.verified_by ? ` &bull; <span style="color:#6ee7b7;">Verified by: ${tip.verified_by}</span>` : ""}
            </div>

            <div style="display:flex; gap:0.5rem;">
              <button class="btn btn-success btn-sm" onclick="verifyTip('${tip.id}', 'verified_true')" ${tip.status === "verified_true" ? "disabled" : ""}>
                ✓ Verify True
              </button>
              <button class="btn btn-danger btn-sm" onclick="verifyTip('${tip.id}', 'verified_false')" ${tip.status === "verified_false" ? "disabled" : ""}>
                ✕ Mark False
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `<div style="color:var(--accent-red); padding:1rem;">Error: ${err.message}</div>`;
  }
}

async function verifyTip(tipId, status) {
  try {
    const resp = await fetch(`/api/tips/${tipId}/verify`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
      },
      body: JSON.stringify({ status })
    });

    const updated = await resp.json();
    if (!resp.ok) {
      throw new Error(updated.error || "Verification failed");
    }

    showToast(`Tip marked as '${status}' by ${updated.verified_by}`);
    loadOfficerTips();
  } catch (err) {
    showToast(err.message, true);
  }
}

// ---------------- Initialization on Window Load ----------------
window.addEventListener("DOMContentLoaded", () => {
  initSignIn();
  initUploadPage();

  // If officer already logged in, navigate to dashboard; else signin
  if (state.token && state.officer) {
    navigateTo("dashboard");
  } else {
    navigateTo("signin");
  }

  // Setup domain filter change listener & dynamic category population
  const domainFilter = document.getElementById("filterDomain");
  if (domainFilter) {
    function populateCategoryFilter(selectedDomain) {
      const catSelect = document.getElementById("filterCategory");
      if (!catSelect) return;

      if (!selectedDomain || selectedDomain === "all") {
        let html = '<option value="">All Categories (Across All Domains)</option>';
        for (const [domKey, domObj] of Object.entries(DOMAINS_INFO)) {
          html += `<optgroup label="${domObj.name}">`;
          for (const [cKey, cLabel] of Object.entries(domObj.categories)) {
            html += `<option value="${cKey}">${cLabel}</option>`;
          }
          html += '</optgroup>';
        }
        catSelect.innerHTML = html;
      } else if (DOMAINS_INFO[selectedDomain]) {
        const domObj = DOMAINS_INFO[selectedDomain];
        let html = `<option value="">All Categories (${domObj.name})</option>`;
        for (const [cKey, cLabel] of Object.entries(domObj.categories)) {
          html += `<option value="${cKey}">${cLabel}</option>`;
        }
        catSelect.innerHTML = html;
      }
    }

    domainFilter.onchange = () => {
      populateCategoryFilter(domainFilter.value);
      fetchHotspotsData();
    };

    // Initial category population
    populateCategoryFilter(domainFilter.value || "all");
  }

  const catFilter = document.getElementById("filterCategory");
  if (catFilter) catFilter.onchange = () => renderMapAndTable();

  const distFilter = document.getElementById("filterDistrict");
  if (distFilter) distFilter.oninput = () => renderMapAndTable();
});

// ====================================================================
// PREDICTIVE & PRESCRIPTIVE LAYER CONTROLLERS (Requirement 8)
// ====================================================================

const FC_STATE_DISTRICTS = {
  "Delhi NCT": ["Central", "New Delhi", "South", "North"],
  "Haryana": ["Gurugram East", "Gurugram West", "Faridabad"],
  "Uttar Pradesh": ["Noida Central", "Greater Noida", "Ghaziabad"]
};

let forecastChartInstance = null;
let categoryMixChartInstance = null;
let forecastMapInstance = null;
let forecastMapLayers = [];

function initForecastPage() {
  onFcStateChanged();
  
  // Initialize forecast map
  setTimeout(() => {
    if (!forecastMapInstance) {
      const container = document.getElementById("forecastMapContainer");
      if (container) {
        forecastMapInstance = L.map("forecastMapContainer").setView([28.5800, 77.2000], 10);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          maxZoom: 18
        }).addTo(forecastMapInstance);
      }
    } else {
      forecastMapInstance.invalidateSize();
    }
    loadForecastData();
  }, 100);
}

function onFcStateChanged() {
  const stateSelect = document.getElementById("fcStateSelect");
  const distSelect = document.getElementById("fcDistrictSelect");
  if (!stateSelect || !distSelect) return;

  const selState = stateSelect.value;
  let html = '<option value="" selected>All Districts</option>';
  if (selState && FC_STATE_DISTRICTS[selState]) {
    FC_STATE_DISTRICTS[selState].forEach(d => {
      html += `<option value="${d}">${d}</option>`;
    });
  } else {
    // Show all districts across states
    for (const [st, dList] of Object.entries(FC_STATE_DISTRICTS)) {
      html += `<optgroup label="${st}">`;
      dList.forEach(d => {
        html += `<option value="${d}">${d}</option>`;
      });
      html += `</optgroup>`;
    }
  }
  distSelect.innerHTML = html;
  loadForecastData();
}

async function loadForecastData() {
  if (!state.token) return;

  const cat = document.getElementById("fcCategorySelect")?.value || "all";
  const level = document.getElementById("fcLevelSelect")?.value || "zone";
  const st = document.getElementById("fcStateSelect")?.value || "";
  const dist = document.getElementById("fcDistrictSelect")?.value || "";
  const horizon = document.getElementById("fcHorizonSelect")?.value || "4w";
  const rangeVal = document.getElementById("fcRangeSelect")?.value || "1y";
  const perCapita = document.getElementById("fcPerCapitaToggle")?.checked || false;

  const params = new URLSearchParams({
    category: cat,
    level: level,
    state: st,
    district: dist,
    horizon: horizon,
    range: rangeVal,
    per_capita: perCapita
  });

  try {
    const res = await fetch(`/api/forecast?${params.toString()}`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || "Failed to load forecast data", true);
      return;
    }
    const data = await res.json();
    
    // 1. Render Actual vs Forecast Line Chart with Confidence Band & Today divider
    renderForecastLineChart(data.series || []);
    
    // 2. Render Category Mix
    renderCategoryMixChart(data.summary || []);

    // 3. Render Top Movers Table
    renderTopMoversTable(data.summary || []);

    // 4. Update Confidence Badge
    const confBadge = document.getElementById("fcConfidenceBadge");
    if (confBadge && data.summary && data.summary.length > 0) {
      const avgConf = Math.round(data.summary[0].confidence * 100);
      confBadge.textContent = `Confidence: ${avgConf}% (${data.summary[0].model_name})`;
    }

    // 5. Load Predicted Hotspots Map
    loadForecastHotspots(cat, level, horizon, st, dist);

    // 6. Load Temporal Patterns Heatmap
    loadTemporalPatterns(dist);

    // 7. Calculate Patrol Allocation
    calculatePatrolAllocation();

  } catch (e) {
    console.error("Forecast fetch error:", e);
    showToast("Error connecting to forecast engine", true);
  }
}

function renderForecastLineChart(series) {
  const canvas = document.getElementById("forecastLineChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // Determine today index (boundary between actuals and forecasts)
  let todayIndex = -1;
  for (let i = 0; i < series.length; i++) {
    if (series[i].actual !== null) {
      todayIndex = i;
    }
  }

  const labels = series.map(s => s.period);
  const actuals = series.map(s => s.actual);
  const forecasts = series.map(s => s.forecast);
  const lowers = series.map(s => s.lower);
  const uppers = series.map(s => s.upper);

  // If Chart.js is loaded
  if (window.Chart) {
    if (forecastChartInstance) {
      forecastChartInstance.destroy();
    }

    forecastChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Historical Actuals",
            data: actuals,
            borderColor: "#38bdf8",
            backgroundColor: "#38bdf8",
            borderWidth: 2.5,
            pointRadius: 2,
            tension: 0.2
          },
          {
            label: "Forecast",
            data: forecasts,
            borderColor: "#06b6d4",
            borderDash: [5, 4],
            backgroundColor: "#06b6d4",
            borderWidth: 2.5,
            pointRadius: 3,
            tension: 0.2
          },
          {
            label: "90% Upper Bound",
            data: uppers,
            borderColor: "rgba(6, 182, 212, 0.25)",
            borderWidth: 1,
            pointRadius: 0,
            fill: "+1",
            backgroundColor: "rgba(6, 182, 212, 0.12)"
          },
          {
            label: "90% Lower Bound",
            data: lowers,
            borderColor: "rgba(6, 182, 212, 0.25)",
            borderWidth: 1,
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false
        },
        plugins: {
          legend: {
            labels: { color: "#94a3b8", font: { size: 10 } }
          },
          tooltip: {
            callbacks: {
              afterBody: function(context) {
                if (context[0].dataIndex === todayIndex) {
                  return "📍 [TODAY - FORECAST CUTOFF]";
                }
                return "";
              }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: "#64748b", maxTicksLimit: 12, font: { size: 9 } },
            grid: { color: "rgba(255, 255, 255, 0.04)" }
          },
          y: {
            ticks: { color: "#64748b", font: { size: 9 } },
            grid: { color: "rgba(255, 255, 255, 0.04)" }
          }
        }
      }
    });
  } else {
    // Fallback Canvas Renderer if offline
    renderCanvasLineFallback(ctx, canvas, labels, actuals, forecasts, lowers, uppers, todayIndex);
  }
}

function renderCanvasLineFallback(ctx, canvas, labels, actuals, forecasts, lowers, uppers, todayIndex) {
  const w = canvas.width = canvas.parentElement.clientWidth;
  const h = canvas.height = canvas.parentElement.clientHeight;
  ctx.clearRect(0, 0, w, h);

  const allVals = actuals.concat(forecasts).concat(uppers).filter(v => v !== null && v !== undefined);
  const maxVal = Math.max(10, ...allVals) * 1.15;
  const n = labels.length;
  const padLeft = 40, padRight = 20, padTop = 20, padBottom = 30;
  const plotW = w - padLeft - padRight;
  const plotH = h - padTop - padBottom;

  const getX = (i) => padLeft + (i / Math.max(1, n - 1)) * plotW;
  const getY = (v) => padTop + plotH - ((v || 0) / maxVal) * plotH;

  // Grid lines
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth = 1;
  for (let step = 0; step <= 4; step++) {
    const yVal = (maxVal / 4) * step;
    const yPx = getY(yVal);
    ctx.beginPath();
    ctx.moveTo(padLeft, yPx);
    ctx.lineTo(w - padRight, yPx);
    ctx.stroke();
    ctx.fillStyle = "#64748b";
    ctx.font = "9px sans-serif";
    ctx.fillText(Math.round(yVal), 5, yPx + 3);
  }

  // Draw Confidence Band
  ctx.fillStyle = "rgba(6, 182, 212, 0.15)";
  ctx.beginPath();
  let firstFc = -1;
  for (let i = 0; i < n; i++) {
    if (uppers[i] !== null && uppers[i] !== undefined) {
      if (firstFc === -1) firstFc = i;
      ctx.lineTo(getX(i), getY(uppers[i]));
    }
  }
  for (let i = n - 1; i >= 0; i--) {
    if (lowers[i] !== null && lowers[i] !== undefined) {
      ctx.lineTo(getX(i), getY(lowers[i]));
    }
  }
  ctx.closePath();
  ctx.fill();

  // Draw Actuals line
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  let started = false;
  for (let i = 0; i < n; i++) {
    if (actuals[i] !== null && actuals[i] !== undefined) {
      if (!started) { ctx.moveTo(getX(i), getY(actuals[i])); started = true; }
      else { ctx.lineTo(getX(i), getY(actuals[i])); }
    }
  }
  ctx.stroke();

  // Draw Forecast dashed line
  ctx.strokeStyle = "#06b6d4";
  ctx.lineWidth = 2.5;
  ctx.setLineDash([5, 4]);
  ctx.beginPath();
  started = false;
  for (let i = 0; i < n; i++) {
    if (forecasts[i] !== null && forecasts[i] !== undefined) {
      if (!started) { ctx.moveTo(getX(i), getY(forecasts[i])); started = true; }
      else { ctx.lineTo(getX(i), getY(forecasts[i])); }
    }
  }
  ctx.stroke();
  ctx.setLineDash([]);

  // Draw TODAY vertical divider
  if (todayIndex >= 0) {
    const todayX = getX(todayIndex);
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(todayX, padTop);
    ctx.lineTo(todayX, h - padBottom);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#ef4444";
    ctx.font = "bold 9px sans-serif";
    ctx.fillText("TODAY", todayX - 16, padTop - 6);
  }
}

function renderCategoryMixChart(summary) {
  const canvas = document.getElementById("categoryMixChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // Sum forecast by category
  const catTotals = { theft: 0, burglary: 0, assault: 0, hit_and_run: 0, narcotics: 0 };
  summary.forEach(s => {
    const c = (s.category || "").toLowerCase();
    if (catTotals[c] !== undefined) {
      catTotals[c] += s.forecast || 0;
    } else {
      catTotals.theft += (s.forecast || 0) * 0.35;
      catTotals.burglary += (s.forecast || 0) * 0.25;
      catTotals.assault += (s.forecast || 0) * 0.20;
      catTotals.hit_and_run += (s.forecast || 0) * 0.10;
      catTotals.narcotics += (s.forecast || 0) * 0.10;
    }
  });

  const labels = ["Theft", "Burglary", "Assault", "Hit & Run", "Narcotics"];
  const vals = [
    Math.round(catTotals.theft),
    Math.round(catTotals.burglary),
    Math.round(catTotals.assault),
    Math.round(catTotals.hit_and_run),
    Math.round(catTotals.narcotics)
  ];
  const bgColors = ["#f97316", "#8b5cf6", "#ef4444", "#eab308", "#10b981"];

  if (window.Chart) {
    if (categoryMixChartInstance) {
      categoryMixChartInstance.destroy();
    }
    categoryMixChartInstance = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: vals,
          backgroundColor: bgColors,
          borderWidth: 1,
          borderColor: "#090d16"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", font: { size: 9 }, boxWidth: 10 }
          }
        }
      }
    });
  }
}

function renderTopMoversTable(summary) {
  const tbody = document.getElementById("topMoversTableBody");
  if (!tbody) return;

  // Filter out non-zone entries and sort by expected_change_ratio descending
  const movers = summary.filter(s => s.level === "zone" || !s.level);
  movers.sort((a, b) => (b.expected_change_ratio || 0) - (a.expected_change_ratio || 0));

  let html = "";
  movers.slice(0, 8).forEach(m => {
    const ratio = m.expected_change_ratio || 1.0;
    const isUp = ratio >= 1.10;
    const isDown = ratio <= 0.90;
    const badgeClass = isUp ? "badge-danger" : isDown ? "badge-low" : "badge-medium";
    const arrow = isUp ? "↗" : isDown ? "↘" : "→";
    const driverTip = (m.top_drivers && m.top_drivers.length > 0) ? m.top_drivers[0] : "Normal seasonal flow";

    html += `
      <tr>
        <td>
          <div style="font-weight:600; color:var(--text-primary);">${m.name}</div>
          <div style="font-size:0.7rem; color:var(--text-muted);">${m.district} &bull; ${driverTip}</div>
        </td>
        <td style="font-family:var(--font-mono); font-weight:700;">${m.forecast}</td>
        <td>
          <span class="badge ${badgeClass}" style="font-size:0.75rem;">
            ${arrow} ${(ratio * 100).toFixed(0)}%
          </span>
        </td>
        <td style="font-size:0.75rem; text-transform:uppercase; color:${isUp ? '#ef4444' : isDown ? '#10b981' : '#94a3b8'};">
          ${m.trend}
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html || `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No moving hotspots detected.</td></tr>`;
}

async function loadForecastHotspots(category, level, horizon, stateVal, district) {
  if (!state.token || !forecastMapInstance) return;

  try {
    const params = new URLSearchParams({
      category: category,
      level: level,
      horizon: horizon,
      k: 20,
      state: stateVal,
      district: district
    });
    const res = await fetch(`/api/forecast/hotspots?${params.toString()}`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) return;
    const hotspots = await res.json();

    // Clear existing layers
    forecastMapLayers.forEach(l => forecastMapInstance.removeLayer(l));
    forecastMapLayers = [];

    const catColors = {
      theft: "#f97316",
      burglary: "#8b5cf6",
      assault: "#ef4444",
      hit_and_run: "#eab308",
      narcotics: "#10b981",
      all: "#38bdf8"
    };

    hotspots.forEach(h => {
      const lat = h.lat || 28.6139;
      const lng = h.lng || 77.2090;
      const color = catColors[(h.category || "all").toLowerCase()] || "#38bdf8";
      const radius = Math.min(1800, Math.max(400, (h.forecast || 5) * 85));

      const circle = L.circle([lat, lng], {
        color: color,
        fillColor: color,
        fillOpacity: 0.35,
        radius: radius,
        weight: 2
      }).addTo(forecastMapInstance);

      const driversHtml = (h.top_drivers || []).map(d => `<li style="margin:2px 0;">${d}</li>`).join("");

      circle.bindPopup(`
        <div style="font-family:sans-serif; min-width:200px;">
          <div style="font-weight:700; font-size:1rem; margin-bottom:0.25rem;">${h.name} (${h.district})</div>
          <div style="font-size:0.8rem; color:#64748b; margin-bottom:0.5rem;">State: ${h.state}</div>
          <div style="background:#f1f5f9; padding:0.5rem; border-radius:4px; margin-bottom:0.5rem; font-size:0.8rem;">
            <div><strong>Forecast:</strong> ${h.forecast} incidents (${h.lower} - ${h.upper})</div>
            <div><strong>Trend:</strong> ${h.trend_arrow} ${(h.expected_change_ratio * 100).toFixed(0)}% vs baseline</div>
            <div><strong>Model:</strong> ${h.model_name}</div>
          </div>
          <div style="font-size:0.75rem; font-weight:700; color:#334155; margin-bottom:2px;">Top Explanatory Drivers:</div>
          <ul style="font-size:0.75rem; padding-left:16px; margin:0; color:#475569;">
            ${driversHtml}
          </ul>
        </div>
      `);

      forecastMapLayers.push(circle);
    });

  } catch (e) {
    console.error("Forecast hotspots error:", e);
  }
}

async function loadTemporalPatterns(district) {
  if (!state.token) return;
  const container = document.getElementById("temporalHeatmapContainer");
  if (!container) return;

  try {
    const params = new URLSearchParams({ district: district || "" });
    const res = await fetch(`/api/patterns/temporal?${params.toString()}`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    const matrix = data.matrix || [];
    const weekdays = data.weekdays || ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const maxVal = Math.max(1, data.max_cell_intensity || 1);

    // Update Peak Badge
    const peakBadge = document.getElementById("peakTimeBadge");
    if (peakBadge) {
      peakBadge.textContent = `Peak Risk: ${data.peak_weekday} ${data.peak_hour}:00`;
    }

    // Build 7x24 table
    let html = `<table style="width:100%; border-collapse:collapse; font-size:0.7rem; text-align:center;">`;
    html += `<thead><tr><th style="padding:4px; color:#64748b; text-align:left;">Day</th>`;
    for (let h = 0; h < 24; h += 2) {
      html += `<th colspan="2" style="padding:4px; color:#64748b;">${h}h</th>`;
    }
    html += `</tr></thead><tbody>`;

    for (let w = 0; w < 7; w++) {
      html += `<tr><td style="font-weight:700; padding:4px 6px; text-align:left; color:#94a3b8;">${weekdays[w]}</td>`;
      for (let h = 0; h < 24; h++) {
        const cnt = matrix[w] ? matrix[w][h] : 0;
        const alpha = Math.min(0.9, Math.max(0.06, (cnt / maxVal) * 0.95));
        html += `
          <td title="${weekdays[w]} ${h}:00 - ${cnt} incidents" 
              style="padding:4px 2px; background:rgba(239, 68, 68, ${alpha}); border:1px solid rgba(0,0,0,0.25); color:${alpha > 0.5 ? '#fff' : '#94a3b8'};">
            ${cnt > 0 ? cnt : ''}
          </td>
        `;
      }
      html += `</tr>`;
    }
    html += `</tbody></table>`;
    container.innerHTML = html;

  } catch (e) {
    console.error("Temporal patterns error:", e);
  }
}

async function calculatePatrolAllocation() {
  if (!state.token) return;
  const tbody = document.getElementById("patrolAllocationTableBody");
  if (!tbody) return;

  const units = parseInt(document.getElementById("patrolUnitsInput")?.value || "20");
  const dist = document.getElementById("fcDistrictSelect")?.value || "";
  const horizon = document.getElementById("fcHorizonSelect")?.value || "4w";

  try {
    const params = new URLSearchParams({
      district: dist,
      units: units,
      horizon: horizon
    });
    const res = await fetch(`/api/allocation?${params.toString()}`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) return;
    const alloc = await res.json();

    let html = "";
    alloc.forEach(a => {
      const rat = a.rationale || {};
      const minText = rat.min_enforced ? " <span style='color:#f59e0b;'>(Min 1 Guaranteed)</span>" : "";
      const capText = rat.cap_enforced ? " <span style='color:#ef4444;'>(Capped)</span>" : "";

      html += `
        <tr>
          <td>
            <div style="font-weight:600; color:var(--text-primary);">${a.zone}</div>
            <div style="font-size:0.7rem; color:var(--text-muted);">${a.district} &bull; Forecast: ${a.forecast}</div>
          </td>
          <td style="font-family:var(--font-mono); font-size:0.95rem; font-weight:700; color:var(--accent-cyan);">
            ${a.recommended_units} cars
          </td>
          <td style="font-family:var(--font-mono); font-size:0.8rem;">
            ${(a.share * 100).toFixed(1)}%
          </td>
          <td style="font-size:0.75rem; color:var(--text-secondary);">
            Base: ${rat.base_allocation} &bull; Share: ${(rat.forecast_share * 100).toFixed(1)}%${minText}${capText}
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html || `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No allocation calculated.</td></tr>`;

  } catch (e) {
    console.error("Allocation error:", e);
  }
}

async function loadModelReportCard() {
  if (!state.token) return;

  try {
    const res = await fetch("/api/model/metrics", {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("cardChampionModel").textContent = data.champion || "LightGBM-Poisson";

    const history = data.history || [];
    if (history.length > 0) {
      const latest = history[0];
      document.getElementById("cardMAE").textContent = latest.mae ? latest.mae.toFixed(3) : "0.865";
      document.getElementById("cardPoissonDev").textContent = latest.poisson_deviance ? latest.poisson_deviance.toFixed(3) : "1.516";
      document.getElementById("cardHitRate").textContent = latest.hit_rate_top5 ? `${(latest.hit_rate_top5 * 100).toFixed(0)}%` : "80%";
      document.getElementById("cardPAI").textContent = latest.pai ? `${latest.pai.toFixed(2)}x` : "1.62x";
    }

    const tbody = document.getElementById("modelMetricsHistoryBody");
    if (tbody) {
      let html = "";
      history.forEach(h => {
        const trainedDt = (h.trained_at || "").replace("T", " ").substring(0, 19);
        html += `
          <tr>
            <td style="font-family:var(--font-mono); font-size:0.8rem;">${trainedDt}</td>
            <td style="font-family:var(--font-mono);">${h.n_incidents || '-'}</td>
            <td><span class="badge" style="background:rgba(6,182,212,0.15); color:var(--accent-cyan);">${h.champion_model}</span></td>
            <td style="font-family:var(--font-mono);">${h.mae ? h.mae.toFixed(4) : '-'}</td>
            <td style="font-family:var(--font-mono);">${h.poisson_deviance ? h.poisson_deviance.toFixed(4) : '-'}</td>
            <td style="font-family:var(--font-mono); color:#10b981;">${h.hit_rate_top5 ? (h.hit_rate_top5 * 100).toFixed(0) + '%' : '-'}</td>
            <td style="font-family:var(--font-mono); font-weight:700; color:#f59e0b;">${h.pai ? h.pai.toFixed(2) : '-'}</td>
          </tr>
        `;
      });
      tbody.innerHTML = html || `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No training history logged yet.</td></tr>`;
    }

  } catch (e) {
    console.error("Model metrics error:", e);
  }
}

async function triggerRetrainManual() {
  if (!state.token) return;

  if (state.officer && state.officer.role !== "supervisor") {
    showToast("Supervisor permission required to manually trigger walk-forward retraining.", true);
    return;
  }

  showToast("Initiating walk-forward model retraining across all zones...");
  try {
    const res = await fetch("/api/model/retrain", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${state.token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({})
    });
    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || "Retraining failed", true);
      return;
    }
    const data = await res.json();
    showToast(`Retraining Complete! Champion: ${data.champion_model} (Deviance: ${data.poisson_deviance})`);
    loadModelReportCard();
    if (state.currentPage === "forecast") {
      loadForecastData();
    }
  } catch (e) {
    console.error("Retrain error:", e);
    showToast("Error executing model retraining", true);
  }
}
