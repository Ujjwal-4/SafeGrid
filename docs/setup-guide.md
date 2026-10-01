# Setup Guide

## Prerequisites

- Python 3.10+ (tested on 3.12)
- Node.js 18+ and npm (only for the AI brief service)
- A modern browser (the map loads Leaflet and OpenStreetMap tiles from the internet)
- Optional: an IBM watsonx.ai project and API key, only if you set `LLM_PROVIDER=ibm_watsonx`. Not needed for the demo.

## Environment Variables

The platform runs with no configuration. The AI brief service reads `src/explain-report-service/.env`:

```bash
cd src/explain-report-service
cp .env.example .env
```

| Variable | Description | Required |
|---|---|---|
| `JWT_SECRET` | Must equal the platform's `JWT_SECRET`. The shipped default matches the platform's dev default. | Yes |
| `SCORING_SOURCE` | `crime_intel_backend` reads the running platform; `sample` uses canned data | Yes |
| `CRIME_INTEL_BASE_URL` | Platform URL (default `http://localhost:8080`) | Yes |
| `CRIME_INTEL_SERVICE_BADGE_ID` / `CRIME_INTEL_SERVICE_PASSWORD` | Service login, used only when a request carries no bearer token | No |
| `LLM_PROVIDER` | `mock` (default, offline) or `ibm_watsonx` | Yes |
| `IBM_API_KEY`, `IBM_PROJECT_ID`, `IBM_URL`, `IBM_MODEL_ID` | Only for `ibm_watsonx`. Never commit real values. | No |
| `PORT` | Default `4100` | No |

Platform: optionally `export JWT_SECRET=...` before starting it (and use the same value in the AI service `.env`).

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Ujjwal-4/bob-ai-hackathon-Team_Rocket.git
cd bob-ai-hackathon-Team_Rocket

# 2. Platform dependencies
cd src/platform
pip install -r requirements.txt

# 3. Load the sample data into SQLite (created at src/platform/data/platform.sqlite)
python3 scripts/ingest_cli.py --file data/mock_fir_sample.xlsx --config configs/narcotics.yaml --store-db
python3 scripts/ingest_cli.py --file data/mock_dial100_logs.csv --config configs/crime.yaml --store-db

# 4. AI brief service dependencies
cd ../explain-report-service
npm install
cp .env.example .env
```

## Running the Application

```bash
# Terminal 1 - platform + dashboard
cd src/platform
python3 server/app.py          # http://localhost:8080

# Terminal 2 - AI brief service
cd src/explain-report-service
npm start                      # http://localhost:4100
```

Open `http://localhost:8080` and sign in with `SUPER-101` / `supervisor_pass` (or `OFFICER-001` / `officer_pass`). The **Upload** page has the **AI Narcotics Bulletin** and **AI Crime Brief** buttons; the tip portal is at the "Anonymous Public Tip Portal" link on the sign-in page.

### Verify it is working

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/auth/login -H 'Content-Type: application/json' \
  -d '{"badge_id":"SUPER-101","password":"supervisor_pass"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s "localhost:8080/api/hotspots?domain=narcotics" -H "Authorization: Bearer $TOKEN" | head -c 300
curl -s "localhost:4100/api/reports/crime?type=weekly&format=json" -H "Authorization: Bearer $TOKEN" | head -c 400
```

## Running Tests

```bash
cd src/platform && python3 scripts/test_platform.py     # starts its own server; end-to-end API + schema checks
cd src/explain-report-service && npm install --no-save supertest && node smoke_test.js   # offline, uses the mock provider
```

## Quick Demo (Optional)

`python3 scripts/generate_mock_data.py` regenerates the synthetic datasets in `src/platform/data/`. Pass `--file`/`--config` pairs to `scripts/ingest_cli.py` to load other files (for example `data/mock_fir_sample.csv`, `data/mock_1930_cyber_narcotics.csv`).

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: jwt` or `yaml` | `pip install -r requirements.txt` in `src/platform` |
| pip says `externally-managed-environment` | Use a virtualenv: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` |
| Map shows no markers | Load data first (Installation step 3), then refresh; the DB is created empty otherwise |
| AI buttons show "Failed to generate AI report" | Check the AI service is running on port 4100 and `JWT_SECRET` matches the platform; a 401 means the secrets differ |
| AI service returns 500 "Platform /api/hotspots returned ..." | The platform is not running at `CRIME_INTEL_BASE_URL` |
| Ingest is slow | With internet access, geocoding is limited to about 1 request/second (Nominatim policy); results are cached, so re-runs are fast. Offline, it falls back to the district gazetteer. |
| 429 on the tip portal | Per-IP limit is 15 tips per minute; wait and retry |
| `ibm_watsonx` provider errors | Set `IBM_API_KEY` and `IBM_PROJECT_ID`; this adapter is unverified against a live endpoint, so check the response shape in `ibmWatsonxProvider.js` |
