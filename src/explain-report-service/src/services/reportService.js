const { explainZones } = require('./explainService');
const { fetchScoredZones } = require('./scoringEngineClient');

/**
 * (a) Monthly narcotics intelligence report: every district, ranked by score
 * descending, each with its rationale + recommended action.
 */
async function generateMonthlyReport(domain, opts = {}) {
  const scoredZones = await fetchScoredZones(domain, 'monthly', opts);
  const explained = await explainZones(scoredZones, 'monthly_report');

  const ranked = [...explained].sort((a, b) => b.score - a.score);

  return {
    report_type: 'monthly_intelligence_report',
    domain,
    generated_at: new Date().toISOString(),
    districts: ranked.map((z, i) => ({
      rank: i + 1,
      zone: z.zone,
      score: z.score,
      risk_level: z.riskLevel,
      factors: z.factors,
      rationale: z.rationale,
      recommended_action: z.recommended_action
    }))
  };
}

/**
 * (b) Weekly patrol deployment brief: top 5 at-risk micro-zones, each with
 * probability rationale, any seasonal/event-spike flags the scoring engine
 * already computed (never invented here), and a redeployment recommendation.
 */
async function generateWeeklyBrief(domain, opts = {}) {
  const scoredZones = await fetchScoredZones(domain, 'weekly', opts);
  const explained = await explainZones(scoredZones, 'weekly_brief');

  const top5 = [...explained].sort((a, b) => b.score - a.score).slice(0, 5);

  return {
    report_type: 'weekly_patrol_deployment_brief',
    domain,
    generated_at: new Date().toISOString(),
    top_zones: top5.map((z, i) => ({
      rank: i + 1,
      zone: z.zone,
      score: z.score,
      risk_level: z.riskLevel,
      factors: z.factors,
      seasonal_flag: z.context.seasonal_flag || false,
      event_flag: z.context.event_flag || false,
      spike_reason: z.context.spike_reason || z.context.categories_trending_up || null,
      rationale: z.rationale,
      redeployment_recommendation: z.recommended_action
    }))
  };
}

module.exports = { generateMonthlyReport, generateWeeklyBrief };
