const { buildRationalePrompt } = require('../promptTemplates/rationalePrompt');
const { generateJson } = require('./llmClient');
const { riskLevelForScore } = require('./riskBucket');

/**
 * Explains ONE already-scored zone. This function:
 *  - never computes a score (riskLevelForScore is a pure bucket lookup on a
 *    score that was already given to it — it does not touch factors or
 *    invent anything)
 *  - passes score/riskLevel/factors to the LLM as fixed facts
 *  - returns only what the LLM was asked to produce: rationale + recommended_action
 *
 * @param {Object} scoredZone - { zone, domain, score, factors, context? }
 * @param {'monthly_report'|'weekly_brief'} [audience]
 * @returns {Promise<{ zone, domain, score, riskLevel, factors, rationale, recommended_action }>}
 */
async function explainZone(scoredZone, audience) {
  const { zone, domain, score, factors, context } = scoredZone;

  if (typeof score !== 'number') {
    throw new Error(`explainZone: "${zone}" is missing a numeric score - this layer only explains, it does not compute one`);
  }
  if (!factors || typeof factors !== 'object') {
    throw new Error(`explainZone: "${zone}" is missing a factors object`);
  }

  const riskLevel = riskLevelForScore(score); // pure compute, no LLM involved

  const { system, user } = buildRationalePrompt({ domain, zone, score, riskLevel, factors, context, audience });
  const { rationale, recommended_action } = await generateJson({ system, user });

  return { zone, domain, score, riskLevel, factors, context: context || {}, rationale, recommended_action };
}

/**
 * Explains a batch of already-scored zones (sequentially, to keep provider
 * rate limits predictable — swap to Promise.all if your provider allows it).
 */
async function explainZones(scoredZones, audience) {
  const explained = [];
  for (const z of scoredZones) {
    explained.push(await explainZone(z, audience));
  }
  return explained;
}

module.exports = { explainZone, explainZones };
