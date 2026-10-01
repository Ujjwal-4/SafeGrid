require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const reportsRoutes = require('./routes/reports');

const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(morgan('tiny'));

app.get('/health', (_req, res) => res.json({ status: 'ok', llm_provider: process.env.LLM_PROVIDER || 'mock' }));
app.use('/api/reports', reportsRoutes);

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 4100;
app.listen(PORT, () => console.log(`[explain-report-service] listening on :${PORT}`));

module.exports = app;
