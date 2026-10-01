process.env.JWT_SECRET = 'test-secret';
process.env.LLM_PROVIDER = 'mock';
process.env.AUTH_REQUIRED = 'false'; // simplify the smoke test; auth itself mirrors the main backend's tested JWT middleware

const jwt = require('jsonwebtoken');

async function main() {
  const app = require('./src/server');
  const request = require('supertest');

  console.log('=== 1. Prompt template is domain-agnostic (no hard-coded domain words) ===');
  const { buildRationalePrompt } = require('./src/promptTemplates/rationalePrompt');
  const promptA = buildRationalePrompt({
    domain: 'narcotics',
    zone: 'District X',
    score: 82,
    riskLevel: 'high',
    factors: { seizure_volume: 0.3, od_admissions: 0.4, verified_tip_density: 0.3 }
  });
  const promptB = buildRationalePrompt({
    domain: 'wildlife_poaching', // a domain that was never coded for anywhere
    zone: 'Sector 3',
    score: 45,
    riskLevel: 'medium',
    factors: { snare_reports: 0.6, ranger_sightings: 0.4 }
  });
  const templateOnlyDifference =
    promptA.system === promptB.system && // system message is identical across domains
    !promptA.system.toLowerCase().includes('narcotics') &&
    !promptA.system.toLowerCase().includes('crime');
  console.log('system prompt has zero hard-coded domain words:', templateOnlyDifference);
  console.log('unseen domain "wildlife_poaching" flows through untouched:', promptB.user.includes('wildlife_poaching'));

  console.log('\n=== 2. riskBucket is pure compute, not LLM ===');
  const { riskLevelForScore } = require('./src/services/riskBucket');
  console.log('82 ->', riskLevelForScore(82), '| 55 ->', riskLevelForScore(55), '| 28 ->', riskLevelForScore(28));

  console.log('\n=== 3. explainZone never invents a score ===');
  const { explainZone } = require('./src/services/explainService');
  try {
    await explainZone({ zone: 'No Score Zone', domain: 'narcotics', factors: { x: 1 } });
    console.log('FAILED: should have thrown for missing score');
  } catch (err) {
    console.log('correctly refused to explain a zone with no given score:', err.message);
  }

  console.log('\n=== 4. Monthly narcotics report (JSON) ===');
  const monthlyRes = await request(app).get('/api/reports/narcotics?type=monthly&format=json');
  console.log('status:', monthlyRes.status);
  console.log(JSON.stringify(monthlyRes.body, null, 2));

  console.log('\n=== 5. Weekly crime patrol brief (JSON) ===');
  const weeklyRes = await request(app).get('/api/reports/crime?type=weekly&format=json');
  console.log('status:', weeklyRes.status);
  console.log(JSON.stringify(weeklyRes.body, null, 2));

  console.log('\n=== 6. Monthly report as PDF ===');
  const fs = require('fs');
  const pdfRes = await request(app).get('/api/reports/narcotics?type=monthly&format=pdf').buffer(true).parse((res, cb) => {
    const chunks = [];
    res.on('data', (c) => chunks.push(c));
    res.on('end', () => cb(null, Buffer.concat(chunks)));
  });
  fs.writeFileSync('/tmp/monthly-report-sample.pdf', pdfRes.body);
  console.log('status:', pdfRes.status, 'content-type:', pdfRes.headers['content-type'], 'bytes:', pdfRes.body.length);

  console.log('\n=== 7. Weekly brief as PDF ===');
  const pdfRes2 = await request(app).get('/api/reports/crime?type=weekly&format=pdf').buffer(true).parse((res, cb) => {
    const chunks = [];
    res.on('data', (c) => chunks.push(c));
    res.on('end', () => cb(null, Buffer.concat(chunks)));
  });
  fs.writeFileSync('/tmp/weekly-brief-sample.pdf', pdfRes2.body);
  console.log('status:', pdfRes2.status, 'content-type:', pdfRes2.headers['content-type'], 'bytes:', pdfRes2.body.length);

  console.log('\n=== 8. Auth enforcement (re-enabled) ===');
  process.env.AUTH_REQUIRED = 'true';
  const unauthedRes = await request(app).get('/api/reports/narcotics?type=monthly&format=json');
  console.log('no token -> status:', unauthedRes.status);
  const token = jwt.sign({ sub: 'u1', badge_id: 'SUP-2001', role: 'supervisor' }, process.env.JWT_SECRET, { expiresIn: '1h' });
  const authedRes = await request(app).get('/api/reports/narcotics?type=monthly&format=json').set('Authorization', `Bearer ${token}`);
  console.log('with token -> status:', authedRes.status);

  console.log('\n✅ SMOKE TEST COMPLETE');
  process.exit(0); // server.js calls app.listen(), so force-exit instead of hanging
}

main().catch((err) => {
  console.error('❌ SMOKE TEST FAILED', err);
  process.exit(1);
});
