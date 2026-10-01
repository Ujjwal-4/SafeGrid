const express = require('express');
const { requireAuth } = require('../middleware/auth');
const { generateMonthlyReport, generateWeeklyBrief } = require('../services/reportService');
const { renderMonthlyReportPdf, renderWeeklyBriefPdf } = require('../pdf/pdfGenerator');

const router = express.Router();

// GET /api/reports/:domain?type=monthly|weekly&format=json|pdf
router.get('/:domain', requireAuth, async (req, res) => {
  const { domain } = req.params;
  const type = (req.query.type || 'monthly').toLowerCase();
  const format = (req.query.format || 'json').toLowerCase();

  if (!['monthly', 'weekly'].includes(type)) {
    return res.status(400).json({ error: 'type must be "monthly" or "weekly"' });
  }
  if (!['json', 'pdf'].includes(format)) {
    return res.status(400).json({ error: 'format must be "json" or "pdf"' });
  }

  const authToken = (req.headers.authorization || '').replace(/^Bearer\s+/i, '') || undefined;

  try {
    if (type === 'monthly') {
      const report = await generateMonthlyReport(domain, { authToken });
      if (format === 'json') return res.json(report);
      return renderMonthlyReportPdf(report, res);
    }

    const report = await generateWeeklyBrief(domain, { authToken });
    if (format === 'json') return res.json(report);
    return renderWeeklyBriefPdf(report, res);
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: `Report generation failed: ${err.message}` });
  }
});

module.exports = router;
