const fetch = require('node-fetch');
const { deriveScoredZonesFromHotspots } = require('./scoreFromHotspots');

/**
 * Adapter for the EXTERNAL scoring engine. This service never computes a
 * score itself — it only calls out to whatever system already produced one
 * and hands the result to explainService.
 *
 * Wire `fetchScoredZones` up to your real scoring engine's API/DB. The
 * sample data below exists only so this deliverable's reports and smoke
 * test can run end-to-end without that engine being reachable from here.
 */

const SAMPLE_MONTHLY_NARCOTICS = [
  {
    zone: 'District X',
    domain: 'narcotics',
    score: 82,
    factors: { seizure_volume: 0.3, od_admissions: 0.4, verified_tip_density: 0.3 }
  },
  {
    zone: 'District Y',
    domain: 'narcotics',
    score: 55,
    factors: { seizure_volume: 0.5, od_admissions: 0.2, verified_tip_density: 0.3 }
  },
  {
    zone: 'District Z',
    domain: 'narcotics',
    score: 28,
    factors: { seizure_volume: 0.2, od_admissions: 0.1, verified_tip_density: 0.7 }
  }
];

const SAMPLE_WEEKLY_CRIME = [
  {
    zone: 'Sector 12 - Market Rd',
    domain: 'crime',
    score: 91,
    factors: { theft_frequency: 0.35, assault_frequency: 0.25, hit_and_run_frequency: 0.4 },
    context: { seasonal_flag: true, event_flag: false, spike_reason: 'festival footfall increase' }
  },
  {
    zone: 'Sector 4 - Bus Depot',
    domain: 'crime',
    score: 76,
    factors: { theft_frequency: 0.6, assault_frequency: 0.1, hit_and_run_frequency: 0.3 },
    context: { seasonal_flag: false, event_flag: true, spike_reason: 'college reopening week' }
  },
  {
    zone: 'Sector 7 - Highway Junction',
    domain: 'crime',
    score: 68,
    factors: { hit_and_run_frequency: 0.7, theft_frequency: 0.2, assault_frequency: 0.1 },
    context: { seasonal_flag: false, event_flag: false }
  },
  {
    zone: 'Sector 2 - Old Town',
    domain: 'crime',
    score: 61,
    factors: { burglary_frequency: 0.5, theft_frequency: 0.5 },
    context: { seasonal_flag: false, event_flag: false }
  },
  {
    zone: 'Sector 9 - Riverside',
    domain: 'crime',
    score: 58,
    factors: { assault_frequency: 0.4, theft_frequency: 0.4, burglary_frequency: 0.2 },
    context: { seasonal_flag: true, event_flag: false, spike_reason: 'monsoon-linked reduced visibility' }
  }
];

/**
 * Pulls hotspot entries from the SafeGrid platform (GET /api/hotspots) and
 * derives per-district { score, factors } from them — deterministic code,
 * no LLM involved. Uses the caller's own JWT when one is passed through
 * (the dashboard does this), otherwise logs in as a service account.
 */
async function fetchFromPlatform(domain, authToken) {
  const base = process.env.CRIME_INTEL_BASE_URL || 'http://localhost:8080';
  let token = authToken;

  if (!token) {
    const badge_id = process.env.CRIME_INTEL_SERVICE_BADGE_ID;
    const password = process.env.CRIME_INTEL_SERVICE_PASSWORD;
    if (!badge_id || !password) {
      throw new Error('No bearer token supplied and CRIME_INTEL_SERVICE_BADGE_ID/PASSWORD are not set');
    }
    const loginRes = await fetch(`${base}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ badge_id, password })
    });
    if (!loginRes.ok) throw new Error(`Platform login failed: ${loginRes.status}`);
    token = (await loginRes.json()).token;
  }

  const res = await fetch(`${base}/api/hotspots?domain=${encodeURIComponent(domain)}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error(`Platform /api/hotspots returned ${res.status}`);
  const hotspots = await res.json();
  return deriveScoredZonesFromHotspots(hotspots, domain);
}

/**
 * @param {string} domain
 * @param {'monthly'|'weekly'} reportType
 * @param {{authToken?: string}} [opts]
 * @returns {Promise<Array>} scored-zone objects: { zone, domain, score, factors, context }
 */
async function fetchScoredZones(domain, reportType, opts = {}) {
  const source = process.env.SCORING_SOURCE || 'sample';

  if (source === 'crime_intel_backend') {
    return fetchFromPlatform(domain, opts.authToken);
  }

  // "sample" source: canned data so the service runs with no platform attached.
  if (domain === 'narcotics' && reportType === 'monthly') return SAMPLE_MONTHLY_NARCOTICS;
  if (domain === 'crime' && reportType === 'weekly') return SAMPLE_WEEKLY_CRIME;
  return [];
}

module.exports = { fetchScoredZones };
