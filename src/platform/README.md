# Statutory Crime & Narcotics Intelligence Data Ingestion Platform

A robust, production-grade, domain-agnostic data ingestion module and intelligence analysis service for law enforcement platforms handling FIR registrations, Dial-100 emergency dispatches, and 1930 cyber/narcotics helpline logs across statutory legal domains.

---

## 🌟 Key Features

1. **Statutory Domain Framework (BNS 2023, NDPS, POCSO, IT Act, BSA)**:
   - Driven entirely by declarative domain configuration files (`.yaml` and `.json`) backed by Indian statutory laws.
   - Citizens and field officers report crimes in everyday action-based terms without needing legal section knowledge.
   - **Supported Statutory Domains**:
     - 🔴 **Crimes Involving Physical Harm & Violence** (`physical_harm`, `#dc2626`): Murder, Attempt to Murder, Grievous Hurt, Kidnapping / Abduction. Governed by BNS 2023.
     - 🟣 **Crimes Targeting Women & Children** (`women_children`, `#9333ea`): Sexual Assault, Domestic Violence, Child Abuse / Exploitation, Stalking / Harassment. Governed by BNS 2023 & POCSO Act 2012.
     - 🟠 **Property Crimes & Financial Theft** (`property_crimes`, `#ea580c`): Theft / Burglary, Robbery / Snatching, Motor Vehicle Theft, Extortion. Governed by BNS 2023.
     - 🔵 **Cybercrimes & Digital Offenses** (`cybercrime`, `#2563eb`): Financial Fraud / UPI Scams, Identity Theft / Impersonation, Cyberstalking / Online Harassment, Unauthorized Access / Hacking. Governed by IT Act 2000 & BNS 2023.
     - 🟢 **Narcotics & Controlled Substances** (`narcotics`, `#16a34a`): Seizure, Overdose Admission, Peddling Activity, Drug Trafficking. Governed by NDPS Act 1985.
     - 🟡 **Public Disturbance, Obstruction & State Offenses** (`public_disturbance`, `#ca8a04`): Rioting / Affray, Destruction of Public Property, Unlawful Assembly, Public Nuisance. Governed by BNS 2023 & PDPP Act 1984.
     - 🌐 **All Domains Unified Intelligence**: Filter `domain=all` cross-correlates and displays hotspots across all domains simultaneously with distinctive domain-specific color markers and interactive legend.

2. **Multi-Format Tabular Ingestion (Excel & CSV)**:
   - Ingests raw `.xlsx` and `.csv` files resembling real-world FIR and emergency call logs.
   - **Intelligent Column Auto-Detection**: Matches location/address, crime category, date/time, source reference, police station, and district headers using normalized regex and alias dictionaries.
   - **Non-Destructive Row Flagging**: Rows with missing or ambiguous critical fields are flagged with specific human-readable diagnostic reasons (`missing location`, `unrecognised category: <value>`, `invalid date`) and confidence penalties instead of being dropped.

3. **OpenStreetMap Nominatim Geocoding with Rate-Limiting**:
   - Geocodes text addresses to `{lat, lng}` using OpenStreetMap Nominatim.
   - Strictly enforces Nominatim's **~1 request/second rate-limit** via an internal locking queue and monotonic timer.
   - Persistent SQLite caching (`geocache.sqlite`) prevents redundant lookups.
   - Offline & high-reliability fallback gazetteer for district centroids and police jurisdictions.

4. **Spatio-Temporal Duplicate Detection**:
   - Identifies likely duplicates across different reporting channels (e.g., an event logged initially via Dial-100 call and subsequently registered as an FIR 1–3 hours later).
   - Matches incidents sharing the same domain category, within **<= 350 meters** (Haversine distance or address token match) and **<= 4.0 hours**.
   - Designates the canonical record by source priority (`FIR > 1930 > Dial-100`) and annotates duplicates with `is_duplicate = True` and `duplicate_of = canonical_id`.

5. **Complete Intelligence REST API & Web Dashboard**:
   - Full implementation of all 13 exact endpoints including JWT officer authentication, multipart file upload, public citizen tip portal with IP rate-limiting, supervisor tip verification, dynamic hotspot computation, and structured intelligence report generation.
   - Clean, modern UI with authenticated views: non-logged-in users only see Login and Public Citizen Portal; after authentication, the full operational dashboard (Hotspots, Predictive Forecast, Patrol Allocation, Model Governance, Upload Data, Review Tips, Reports) becomes available.

6. **Predictive Time-Series Forecasting & Model Governance**:
   - **Hierarchical Rollup**: Bottom-up time-series aggregation from Zone -> District -> State levels across multiple forecast horizons (`4w`, `3m`, `6m`) and historical ranges (`6m`, `1y`, `all`).
   - **Ensemble Forecasting Models**: Evaluates multiple model architectures via walk-forward cross-validation:
     - Baselines: Last-Period Naive, Seasonal Naive (52-week lag), Moving Average (4-week / 8-week).
     - Parametric / Count Models: Holt-Winters Exponential Smoothing, Negative Binomial GLM (IRLS fit for overdispersed crime counts).
     - Machine Learning: Gradient Boosted Decision Trees (GBDT) with Poisson deviance loss.
     - Online Blending: Exponentially weighted model ensemble with 90% conformal prediction intervals.
   - **Explainable SHAP Drivers**: Decomposes predicted spikes into interpretable factors (e.g., holiday surge, recent 4-week trend momentum, verified citizen tip density).
   - **Top-K Emerging Hotspots & 7x24 Temporal Matrix**: Evaluates spatial risk with directional trend vectors (`↗`, `→`, `↘`) and maps 168-cell weekday x hour incident concentrations.

7. **Prescriptive Patrol Resource Allocation**:
   - Optimal patrol unit apportionment using the **Hamilton-Hare Largest Remainder Method**.
   - Enforces a minimum service guarantee of at least 1 unit per active zone and a maximum cap (<= 40% of fleet) to prevent over-policing.
   - Generates transparent, numeric explainability rationales for supervisory review.

8. **Strict Civil Liberties & Area-Level Guardrails**:
   - All models operate exclusively at the spatial zone/geographic level.
   - No individual, demographic, personal, or predictive person-profiling data is ever collected, stored, or processed.

---

## 📁 Repository Structure

```
src/platform/
├── app.py                       # Root launcher for the platform service
├── requirements.txt             # Python dependencies
├── configs/                     # Statutory domain definitions (YAML + JSON)
│   ├── physical_harm.yaml / .json
│   ├── women_children.yaml / .json
│   ├── property_crimes.yaml / .json
│   ├── cybercrime.yaml / .json
│   ├── narcotics.yaml / .json
│   ├── public_disturbance.yaml / .json
│   └── crime.yaml / .json
├── core/
│   ├── models.py                # Data models: Incident, Tip, HotspotEntry, User
│   ├── config_loader.py         # Config validation, statutory metadata, deep category synonyms
│   ├── tabular_parser.py        # Excel (.xlsx) & CSV parser, column auto-detection, row flagging
│   ├── geocoder.py              # Nominatim geocoder with 1s queue rate limiter, cache & fallback
│   ├── deduplicator.py          # Spatio-temporal incident deduplicator
│   ├── indicator_engine.py      # Indicator scoring, cross-domain hotspot clustering & reports
│   ├── database.py              # SQLite storage layer with model_metrics and audit_logs tables
│   ├── synthetic_forecast_generator.py # 3-year multi-state synthetic generator with Indian calendar
│   ├── feature_engine.py        # Lags 1-8, rolling stats, cyclical harmonics, tips & spatial features
│   ├── forecasting_models.py    # Naive, Holt-Winters, Negative Binomial GLM, GBDT, conformal intervals
│   ├── allocation_engine.py     # Hamilton-Hare patrol allocation with minimums and caps
│   └── predictive_coordinator.py # Hierarchical rollup, SHAP drivers, top-K hotspots & temporal matrix
├── data/
│   ├── mock_synthetic_3yr_incidents.csv # Pre-generated 3-year benchmark dataset (19,800+ records)
│   ├── mock_physical_harm_indicators.csv
│   ├── mock_women_children_indicators.csv
│   ├── mock_property_crimes_indicators.csv
│   ├── mock_cybercrime_indicators.csv
│   ├── mock_narcotics_indicators.csv
│   ├── mock_public_disturbance_indicators.csv
│   ├── mock_fir_sample.xlsx     # Realistic FIR log sample (Excel)
│   ├── mock_fir_sample.csv      # Realistic FIR log sample (CSV)
│   └── paired_duplicates_meta.json
├── frontend/
│   ├── index.html               # SPA with Leaflet maps, Chart.js forecasting, heatmap & allocation
│   ├── css/styles.css           # Modern dark-theme styling, statutory badges, responsive layout
│   └── js/app.js                # Map engine, dynamic charts, heatmap renderer, allocation calculator
├── server/
│   ├── app.py                   # Multi-threaded REST API server with 13 endpoints (port 8080)
│   ├── auth.py                  # JWT authentication & claims verification
│   └── multipart_parser.py      # Zero-dependency multipart form-data parser
├── scripts/
│   ├── generate_forecast_data.py# Script to generate 3-year synthetic history & seed DB
│   ├── evaluate_forecast.py     # Walk-forward backtesting evaluation benchmark
│   ├── generate_mock_data.py    # Multi-domain mock data generator and DB seeder
│   ├── ingest_cli.py            # Standalone CLI tool to ingest Excel/CSV files
│   └── test_platform.py         # 100% passing end-to-end verification test suite (13 endpoints)
└── README.md
```

---

## 🔑 Default Credentials

| Username / Badge ID | Password | Role | Access Level |
|---|---|---|---|
| `admin` | `admin_pass` | `supervisor` | Full administrative, supervisor & retrain access |
| `ADMIN-001` | `admin_pass` | `supervisor` | Full administrative, supervisor & retrain access |
| `SUPER-101` | `supervisor_pass` | `supervisor` | Supervisor access (tip verification, reports, retrain) |
| `OFFICER-001` | `officer_pass` | `officer` | Ingestion, hotspot maps, forecasts, incident review |

---

## 🚀 Quickstart & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate 3-Year Historical Data & Seed Platform
```bash
python scripts/generate_forecast_data.py
```

### 3. Run Walk-Forward Model Evaluation Benchmark
```bash
python scripts/evaluate_forecast.py
```

### 4. Run Verification Test Suite (13 Endpoints & Core Engines)
```bash
python scripts/test_platform.py
```

### 5. Start Platform Service
```bash
python app.py
```
Open your browser at `http://localhost:8080`.

---

## 🌐 REST API Endpoints

### Core Intelligence & Ingestion
- `POST /api/auth/login` — Authenticate officer/supervisor credentials, returns JWT token.
- `POST /api/upload` — Ingest CSV or XLSX incident logs; returns clean incidents and flagged rows with human-readable diagnostic reasons. Triggers background model retrain.
- `POST /api/tips` — Public rate-limited citizen tip portal with statutory evidence guidance.
- `GET /api/tips?status=pending&district=` — List submitted tips (officer/supervisor only).
- `PATCH /api/tips/:id/verify` — Supervisor endpoint to verify or reject citizen tips.
- `GET /api/hotspots?domain=all` — Dynamic hotspot detection across all statutory domains with color attributes.
- `GET /api/configs` — Returns active domain configurations and statutory metadata.
- `GET /api/reports/:domain` — Generates executive intelligence reports, district rankings, and cluster breakdowns.

### Predictive & Prescriptive Layer
- `GET /api/forecast?category=&level=&state=&district=&horizon=4w|3m|6m&range=6m|1y|all` — Multi-level time-series forecast series with 90% prediction intervals, baseline comparisons, expected change ratios, and top SHAP drivers.
- `GET /api/forecast/hotspots?category=&level=&horizon=&k=` — Top-K ranked predictive hotspots with trend arrows (`↗`, `→`, `↘`), coordinates, and forecast counts.
- `GET /api/patterns/temporal?zone=&category=` — 7 weekdays x 24 hours (168 cells) incident frequency heatmap matrix.
- `GET /api/allocation?district=&units=&horizon=` — Prescriptive patrol allocation with minimum service guarantees, zone caps, and Hamilton-Hare apportionment.
- `GET /api/model/metrics` — Champion model governance metadata, MAE, Poisson deviance, Hit@5, PAI, and training history audit log.
- `POST /api/model/retrain` — Supervisor-only trigger to execute walk-forward model retraining.
