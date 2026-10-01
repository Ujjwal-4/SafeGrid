const PDFDocument = require('pdfkit');

function addHeader(doc, title, domain) {
  doc.fontSize(18).text(title, { underline: true });
  doc.moveDown(0.3);
  doc.fontSize(10).fillColor('gray').text(`domain: ${domain}  |  generated: ${new Date().toISOString()}`);
  doc.moveDown(1);
  doc.fillColor('black');
}

function renderMonthlyReportPdf(report, res) {
  const doc = new PDFDocument({ margin: 40 });
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `attachment; filename="${report.domain}-monthly-intelligence-report.pdf"`);
  doc.pipe(res);

  addHeader(doc, 'Monthly Intelligence Report', report.domain);

  report.districts.forEach((d) => {
    doc.fontSize(13).fillColor('black').text(`${d.rank}. ${d.zone} — score ${d.score} (${d.risk_level})`, { continued: false });
    doc.fontSize(9).fillColor('gray').text(
      `factors: ${Object.entries(d.factors).map(([k, v]) => `${k}=${v}`).join(', ')}`
    );
    doc.moveDown(0.2);
    doc.fontSize(11).fillColor('black').text(d.rationale);
    doc.moveDown(0.2);
    doc.fontSize(11).fillColor('#1a4d8f').text(`Recommended action: ${d.recommended_action}`);
    doc.moveDown(1);
  });

  doc.end();
}

function renderWeeklyBriefPdf(report, res) {
  const doc = new PDFDocument({ margin: 40 });
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `attachment; filename="${report.domain}-weekly-patrol-brief.pdf"`);
  doc.pipe(res);

  addHeader(doc, 'Weekly Patrol Deployment Brief — Top 5 At-Risk Micro-Zones', report.domain);

  report.top_zones.forEach((z) => {
    doc.fontSize(13).fillColor('black').text(`${z.rank}. ${z.zone} — score ${z.score} (${z.risk_level})`);
    doc.fontSize(9).fillColor('gray').text(
      `factors: ${Object.entries(z.factors).map(([k, v]) => `${k}=${v}`).join(', ')}`
    );

    const flags = [];
    if (z.seasonal_flag) flags.push('seasonal spike');
    if (z.event_flag) flags.push('event spike');
    if (flags.length) {
      doc.fontSize(9).fillColor('#a15c00').text(
        `flags: ${flags.join(', ')}${z.spike_reason ? ` (${z.spike_reason})` : ''}`
      );
    }

    doc.moveDown(0.2);
    doc.fontSize(11).fillColor('black').text(z.rationale);
    doc.moveDown(0.2);
    doc.fontSize(11).fillColor('#1a4d8f').text(`Redeployment recommendation: ${z.redeployment_recommendation}`);
    doc.moveDown(1);
  });

  doc.end();
}

module.exports = { renderMonthlyReportPdf, renderWeeklyBriefPdf };
