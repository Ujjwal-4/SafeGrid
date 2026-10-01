/**
 * Deterministic score -> risk_level mapping. This is COMPUTE, not explanation:
 * it never calls the LLM and the LLM is never asked to decide this bucket —
 * only to narrate why a zone landed in the bucket it's given.
 */
function riskLevelForScore(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) {
    throw new Error('riskLevelForScore requires a numeric score');
  }
  if (score >= 70) return 'high';
  if (score >= 40) return 'medium';
  return 'low';
}

module.exports = { riskLevelForScore };
