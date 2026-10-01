/**
 * ONE parametrized prompt template, reused by both report generators.
 *
 * Hard rules baked into the prompt itself:
 *  - The model is given the score and risk_level as ALREADY DECIDED facts.
 *    It is explicitly told never to invent, adjust, or re-derive them.
 *  - Every factor name/value comes verbatim from the caller — the template
 *    never hard-codes "narcotics", "crime", or any other domain vocabulary.
 *    The {domain} variable is the only place domain identity appears, and it
 *    is used purely as a label ("this {domain} zone"), not as branching logic.
 *
 * @param {Object} input
 * @param {string} input.domain - e.g. "narcotics", "crime", or any future domain
 * @param {string} input.zone - zone/district/micro-zone name
 * @param {number} input.score - pre-computed risk score (0-100), given, not generated
 * @param {'high'|'medium'|'low'} input.riskLevel - pre-computed bucket, given, not generated
 * @param {Object<string, number>} input.factors - factor name -> contribution weight (0-1)
 * @param {Object} [input.context] - optional extra signals the scoring engine
 *        already computed and is handing over as fact (e.g. seasonal/event
 *        spike flags). Never fabricated by the LLM — only narrated if present.
 * @param {'monthly_report'|'weekly_brief'} [input.audience] - shapes tone/length only
 * @returns {{ system: string, user: string }} messages for a chat-completion call
 */
function buildRationalePrompt({ domain, zone, score, riskLevel, factors, context, audience }) {
  if (!domain || !zone || typeof score !== 'number' || !riskLevel || !factors) {
    throw new Error('buildRationalePrompt: domain, zone, score, riskLevel, and factors are required');
  }

  const factorLines = Object.entries(factors)
    .sort((a, b) => b[1] - a[1]) // largest contributor first
    .map(([name, weight]) => `- ${name}: ${weight}`)
    .join('\n');

  const contextLines = context && Object.keys(context).length
    ? Object.entries(context)
        .map(([name, value]) => `- ${name}: ${value}`)
        .join('\n')
    : '(none provided)';

  const audienceHint =
    audience === 'weekly_brief'
      ? 'This is for a Station House Officer deciding where to redeploy patrols this week. Be tactical and concrete.'
      : audience === 'monthly_report'
      ? 'This is for a monthly intelligence report read by district commanders. Be concise and strategic.'
      : 'Be concise and concrete.';

  const system = [
    'You are a report-writing assistant for a public-safety intelligence platform.',
    'You NEVER compute, invent, adjust, re-derive, or guess a score, a risk level, or a factor value.',
    'Every number you are given below is already final and correct - your only job is to explain it in plain language.',
    'If asked to output JSON, output ONLY that JSON object and nothing else - no markdown fences, no preamble.'
  ].join(' ');

  const user = [
    `Domain: ${domain}`,
    `Zone: ${zone}`,
    `Pre-computed risk score (0-100, already final - do not change it): ${score}`,
    `Pre-computed risk level (already final - do not change it): ${riskLevel}`,
    '',
    'Contributing factors (name: contribution weight, already final, sum need not be 1):',
    factorLines,
    '',
    'Additional context signals already computed upstream (narrate only if present, never invent your own):',
    contextLines,
    '',
    audienceHint,
    '',
    'Return ONLY a JSON object with this exact shape:',
    '{',
    `  "rationale": "<2-4 sentences explaining WHY this zone is ${riskLevel} risk for ${domain}, naming the specific factors above that drove it, in descending order of contribution>",`,
    '  "recommended_action": "<one concrete, proportionate next step for a decision-maker, grounded only in the factors and context given above>"',
    '}'
  ].join('\n');

  return { system, user };
}

module.exports = { buildRationalePrompt };
