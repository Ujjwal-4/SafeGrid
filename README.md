# 🛡️ SafeGrid: State-to-Zone Crime Hotspot Intelligence Platform

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Team_Rocket |
| **Track** | AI |
| **Team Lead** | Ujjwal Shakya |
| **Members** | Ujjwal Shakya (Leader), Lakshya Samay Singh, Kshitij Sharma, Ruthvik Kattamanchi |

---

## 🚀 Quickstart for Evaluators & Judges (Under 60 Seconds)

### Option A: One-Click Docker (Recommended - Any OS)
```bash
docker compose up --build
```
*(Or double-click `start.sh` on Linux/macOS, or `start.bat` on Windows)*.

Open your browser at: 👉 **`http://localhost:8080`**

### Option B: Native Python (No Docker Required)
If Docker is not installed, SafeGrid runs with pure standard-library Python (zero mandatory external dependencies):
```bash
cd src/platform
python3 app.py
```
Open your browser at: 👉 **`http://localhost:8080`**

### 🔑 Test Credentials:
| Role | Username | Password | Access Level |
|---|---|---|---|
| **Supervisor / Admin** | `admin` *(or `ADMIN-001`)* | `admin_pass` | Full system access, all districts, Retraining, Reports |
| **Supervisor** | `SUPER-101` | `supervisor_pass` | Tip verification, reports, retraining |
| **Field Officer** | `OFFICER-001` | `officer_pass` | Ingestion, hotspot maps, forecasts, patrol allocation |

---

## 🎯 Problem Statement

Crime data is recorded at police-station level but managed across districts and states, with no unified view. Officers and supervisors see FIRs, Dial-100 calls and 1930 helpline logs as separate silos, so hotspots — especially ones nobody has reported yet — surface late, and enforcement stays reactive.

---

## 💡 Solution

SafeGrid ingests messy FIR / Dial-100 / 1930 spreadsheets, cleans, geocodes and de-duplicates them into one incident model, and maps **raw crime frequency by category** with week-over-week / month-over-month trend on a live map. An **anonymous, rate-limited public tip portal** captures activity that never reached a police record, and an **AI briefing layer** turns the computed numbers into plain-language district rationales and recommended actions — the LLM only narrates scores that code has already computed; it never invents one.

---

## ✨ Key Features

- **Domain-agnostic ingestion:** `.xlsx`/`.csv` files are parsed with column auto-detection and category-synonym normalisation, driven entirely by YAML/JSON domain configs (`narcotics`, `crime`, or your own). Bad rows are flagged with reasons (`MISSING_LOCATION`, `UNMAPPED_CATEGORY`, `INVALID_DATETIME`), never silently dropped.
- **Geocoding + cross-channel de-duplication:** Nominatim geocoding at ≤1 req/s with a SQLite cache and offline gazetteer fallback; the same event logged via Dial-100 and later as an FIR (≤350 m, ≤4 h) is collapsed to one canonical record (FIR > 1930 > Dial-100).
- **Frequency hotspot map:** Leaflet dashboard with one circle per district/category sized by **raw incident count** (not an opaque risk score), with previous-period count and ▲/▼/▬ trend, plus a synchronised filter bar and table.
- **Anonymous public tip portal:** no login, no names/phones/emails collected, map-pin location picker, per-IP rate limiting; officers review, verify or reject tips and verified tips feed the hotspot counts.
- **AI briefs (LLM narration layer):** a Monthly Narcotics Bulletin and a Weekly Crime Patrol Brief (top-5 zones with redeployment recommendation), as JSON or PDF, from one shared domain-agnostic prompt template. Compute and explain are strictly separated in code.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3, JavaScript (Node.js + browser) |
| **Frameworks** | Python stdlib `http.server` (REST API), Express (AI brief service), Leaflet.js (map) |
| **IBM Technologies** | watsonx.ai text-generation adapter (built from IBM's public API docs; **not yet verified against a live endpoint** — see limitations) |
| **Databases** | SQLite (incidents, tips, users, geocode cache) |
| **Other** | JWT (PyJWT / jsonwebtoken), PDFKit, OpenStreetMap Nominatim, GitHub Actions |

---

## 📁 Repository Structure

```
├── src/
│   ├── platform/               # Python: ingestion, REST API, dashboard
│   │   ├── core/               #   parser, geocoder, deduplicator, hotspot/indicator engine, SQLite layer
│   │   ├── server/             #   REST API + JWT auth + multipart parser
│   │   ├── frontend/           #   dashboard, upload, tip portal, tip review (Leaflet)
│   │   ├── configs/            #   narcotics / crime domain configs (YAML + JSON)
│   │   ├── data/               #   sample FIR / Dial-100 / 1930 datasets
│   │   └── scripts/            #   ingest CLI, mock-data generator, test suite
│   └── explain-report-service/ # Node: LLM-narrated briefs (JSON/PDF)
├── docs/                       # problem, solution, architecture, setup
├── demo/                       # demo video / live demo links, screenshots
├── presentation/               # slide deck
└── submission.yaml             # structured submission metadata
```

---

## ⚡ How to Run

Full details (prerequisites, env vars, troubleshooting) are in [`docs/setup-guide.md`](docs/setup-guide.md).

```bash
# 1. Clone the repo
git clone https://github.com/Ujjwal-4/bob-ai-hackathon-Team_Rocket.git
cd bob-ai-hackathon-Team_Rocket/src/platform

# 2. Install + load sample data
pip install -r requirements.txt
python3 scripts/ingest_cli.py --file data/mock_fir_sample.xlsx --config configs/narcotics.yaml --store-db
python3 scripts/ingest_cli.py --file data/mock_dial100_logs.csv --config configs/crime.yaml --store-db

# 3. Run the platform (dashboard at http://localhost:8080)
python3 server/app.py

# 4. In a second terminal, run the AI brief service (port 4100)
cd ../explain-report-service
npm install
cp .env.example .env
npm start
```

Demo login: badge `SUPER-101` / password `supervisor_pass`.

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/](presentation/) |

---

## ⚠️ Known Limitations

- **Geographic hierarchy:** the pitch is State → District → Zone, but the current build maps and aggregates at **district** level only. `geo_unit` is config-driven, so a state roll-up and sub-district zones are a schema/UI extension, not yet implemented.
- **Tip-portal hardening is partial:** per-IP rate limiting (15 tips/min, in memory) is enforced server-side, but the CAPTCHA is a client-side code check, `is_high_priority`/`is_urgent` are accepted from the client rather than derived from corroboration, and the "expires in N days" badge is display-only — there is no automatic tip-deletion job yet.
- **Two scoring paths:** the platform's own report uses a weighted composite; the AI briefs use a deterministic score derived from frequency counts (scaled against the busiest district in the window), so "high" means "busiest relative to peers", not an absolute threshold.
- **AI provider:** briefs run on a deterministic offline mock provider by default. The IBM watsonx.ai adapter is implemented but has not been verified against a live endpoint. Seasonal/event flags are not sourced from any calendar yet; the weekly brief shows categories trending up instead.
- **Security:** JWT secret defaults to a dev value unless `JWT_SECRET` is set; demo passwords are SHA-256 hashed without salt; the API is plain HTTP. Not production-ready.
- Sample data is synthetic.

---

## 🏅 What We're Most Proud Of

The **compute/explain split**: every number on the map and in the AI briefs is produced by deterministic code from real ingested records, and the LLM is only ever handed finished scores to narrate — `explainZone` refuses to run without one. Alongside it, the ingestion pipeline (non-destructive row flagging, geocode cache with a rate-limited queue, and cross-channel de-duplication) is what makes a single trustworthy district view possible from three inconsistent sources.

---
