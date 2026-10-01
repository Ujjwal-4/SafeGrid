# Explanation & Reporting Layer

Narrates pre-computed risk scores. **Never computes or invents a score** — it
only explains numbers a scoring engine already produced.

## LLM providers

- `mock` (default): deterministic, offline, same interface as a real provider. The demo and `smoke_test.js` use it.
- `ibm_watsonx`: IBM Cloud IAM token exchange + watsonx.ai text generation
  (`src/services/llmProviders/ibmWatsonxProvider.js`). It was written from IBM's public API docs and is **not verified
  against a live endpoint**; confirm `parseResponseText` against your project's real response before relying on it.
  Credentials come only from environment variables (`IBM_API_KEY`, `IBM_PROJECT_ID`) — never commit them.

Swapping providers only touches `src/services/llmClient.js`; the prompt template, explain service, report builders and routes are provider-agnostic.

## Setup

```bash
npm install
cp .env.example .env      # defaults to LLM_PROVIDER=mock, works with zero credentials
npm start
```

## Endpoint

`GET /api/reports/:domain?type=monthly|weekly&format=json|pdf`

- `type=monthly` -> ranked list of every district with score, rationale and a recommended action
- `type=weekly` -> top 5 zones with rationale, categories trending up, and a redeployment recommendation for the SHO

### Scoring sources (`SCORING_SOURCE`)

- `crime_intel_backend` (used by SafeGrid): calls the platform's `GET /api/hotspots` with the caller's own bearer token
  (or a service login if none), then `src/services/scoreFromHotspots.js` derives per-district `score` (district
  total frequency scaled 0-100 against the busiest district) and `factors` (each category's share). Pure code, no LLM.
- `sample`: canned data in `scoringEngineClient.js`, so the service runs standalone.

`seasonal_flag` / `event_flag` are only populated if a scoring source supplies them; the platform does not, so the
weekly brief reports `categories_trending_up` in `spike_reason` instead.

## Architecture — compute/explain separation

```
scoringEngineClient.fetchScoredZones()   <- COMPUTE (external, mocked here)
        |
        v
explainService.explainZone()             <- riskLevelForScore() is pure compute (no LLM)
        |                                    buildRationalePrompt() + llmClient.generateJson()
        |                                    is the ONLY place the LLM is called, and only
        |                                    to narrate score+factors it was already given
        v
reportService.generate{Monthly,Weekly}() <- assembles/ranks explained zones (no LLM, no scoring)
        |
        v
pdfGenerator.render{...}Pdf()            <- pure formatting
```

The prompt template (`src/promptTemplates/rationalePrompt.js`) is the single
shared template behind both report types. It takes `{domain, zone, score,
riskLevel, factors, context}`, states the score/risk_level as already-final
facts the model must not alter, and is 100% domain-agnostic — `{domain}` is
interpolated as a label only; nothing in the template branches on it or
hard-codes "narcotics"/"crime". The smoke test proves this by running an
invented domain (`wildlife_poaching`) through the exact same template with
zero code changes.

## Testing

`smoke_test.js` runs the whole pipeline offline (mock provider, no network
needed) and:
1. Confirms the prompt template has zero hard-coded domain words and handles
   an unseen domain unchanged.
2. Confirms `riskLevelForScore` is pure compute.
3. Confirms `explainZone` refuses to run if no score is given (compute/explain
   boundary enforced in code, not just by convention).
4. Generates and prints both reports as JSON.
5. Generates both reports as PDF (written to `sample-pdfs/` for reference).
6. Confirms auth is enforced when `AUTH_REQUIRED=true`.

```bash
npm install --no-save supertest
node smoke_test.js
```

## Known trade-offs (given scope)

- `ibmWatsonxProvider.js` is unverified against a live IBM endpoint (no
  network access here) — treat it as a starting point, not a guarantee.
- `explainZones` calls the provider sequentially; parallelize with
  `Promise.all` if your provider's rate limits allow it.
- No caching layer — if the same domain/type is requested repeatedly in a
  short window, consider caching the explained report for a few minutes to
  avoid redundant LLM calls.
