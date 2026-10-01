/**
 * Deterministic, offline stand-in for a real LLM call. It follows the exact
 * same contract as a real provider (system+user in, JSON string out) so
 * swapping providers never touches explainService or the report generators.
 *
 * This is what generated the sample PDFs/report JSON in this deliverable,
 * since this sandbox has no network path to any external LLM API.
 */
async function generate({ system, user }) {
  // Pull the already-computed facts back out of the prompt text so the mock
  // can produce a plausible, consistent narrative without re-deriving them
  // (it never invents a score/level - it just echoes what the template put in).
  const zoneMatch = user.match(/^Zone: (.+)$/m);
  const domainMatch = user.match(/^Domain: (.+)$/m);
  const levelMatch = user.match(/risk level \(already final - do not change it\): (\w+)/);
  const factorBlock = user.split('Contributing factors')[1].split('Additional context')[0];
  const factorLines = factorBlock
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.startsWith('-'))
    .map((l) => l.replace(/^- /, ''));

  const zone = zoneMatch ? zoneMatch[1] : 'the zone';
  const domain = domainMatch ? domainMatch[1] : 'this domain';
  const level = levelMatch ? levelMatch[1] : 'medium';
  const topFactors = factorLines.slice(0, 2).map((f) => f.split(':')[0]).join(' and ');

  const rationale = `${zone} is classified ${level} risk for ${domain}, driven primarily by ${topFactors || 'the listed factors'}. These contributions outweigh the remaining factors in this window.`;

  const recommended_action =
    level === 'high'
      ? `Prioritize ${zone} for immediate follow-up and resource allocation this cycle.`
      : level === 'medium'
      ? `Maintain routine monitoring of ${zone} and re-assess if any single factor above trends upward.`
      : `No elevated action needed for ${zone}; continue standard monitoring.`;

  return JSON.stringify({ rationale, recommended_action });
}

module.exports = { generate };
