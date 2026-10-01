/**
 * Pure, deterministic bridge: platform hotspot entries -> { score, factors }.
 *
 * The platform's GET /api/hotspots returns frequency counts per district and
 * category (no weighted score, by design). The LLM layer needs a pre-computed
 * score to narrate, and is never allowed to invent one — so it is derived
 * here, in plain code:
 *   - factors: each category's share of the district's total frequency
 *   - score:   the district's total frequency, scaled 0-100 against the
 *              busiest district in the same response (relative, not absolute)
 *   - context: categories whose trend is "up" (a restatement of a fact the
 *              platform already computed, never an invented signal)
 *
 * @param {Array<{district, category, frequency, trend}>} hotspots
 * @param {string} domain
 */
function deriveScoredZonesFromHotspots(hotspots, domain) {
  const byZone = new Map();
  for (const h of hotspots) {
    if (!byZone.has(h.district)) byZone.set(h.district, []);
    byZone.get(h.district).push(h);
  }

  const totals = new Map();
  for (const [zone, entries] of byZone) {
    totals.set(zone, entries.reduce((sum, e) => sum + (e.frequency || 0), 0));
  }
  const maxTotal = Math.max(0, ...totals.values());

  const scored = [];
  for (const [zone, entries] of byZone) {
    const total = totals.get(zone);
    if (total === 0) continue;

    const factors = {};
    for (const e of entries) {
      if (!e.frequency) continue;
      factors[e.category] = Math.round((e.frequency / total) * 100) / 100;
    }
    const trendingUp = entries.filter((e) => e.trend === 'up').map((e) => e.category);

    scored.push({
      zone,
      domain,
      score: Math.round((total / maxTotal) * 100),
      factors,
      context: trendingUp.length ? { categories_trending_up: trendingUp.join(', ') } : {}
    });
  }
  return scored;
}

module.exports = { deriveScoredZonesFromHotspots };
