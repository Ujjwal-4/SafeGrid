# Solution Overview

## What We Built

SafeGrid is a crime and narcotics hotspot intelligence platform. It takes the messy spreadsheets police already produce, cleans them into one incident model, shows where and how often each category of crime is occurring (with trend), lets the public flag unseen hotspots anonymously, and generates short AI-written briefs that explain the numbers and recommend an action.

## How It Works

1. **Ingest.** An officer uploads an `.xlsx`/`.csv` (FIR, Dial-100 or 1930 log). Columns are auto-detected; categories are normalised through the domain config's synonym map; rows that cannot be trusted are *flagged with a reason*, not dropped.
2. **Geocode.** Addresses are geocoded through OpenStreetMap Nominatim at ≤1 request/second, cached in SQLite, with an offline gazetteer fallback for district centroids.
3. **De-duplicate.** Incidents of the same category within 350 m and 4 hours across channels are collapsed into one canonical record (FIR > 1930 > Dial-100).
4. **Aggregate.** Hotspots are computed as raw frequency per district and category for the configured window (weekly/monthly) with the previous window's count and an up/down/flat trend. Verified public tips are added to the counts.
5. **Collect tips.** The anonymous portal (no login, no personal data, per-IP rate limit, map-pin picker) creates `pending` tips; officers verify or reject them.
6. **Explain.** The AI brief service reads the platform's hotspot data, derives a deterministic score and factor breakdown in code, and asks an LLM only to narrate it: why the district is high/medium/low, and one recommended action. Output is JSON or PDF.

## Architecture Diagram

See [`architecture.md`](architecture.md).

```
Excel/CSV -> parse -> geocode -> de-duplicate -> SQLite -> hotspots (frequency + trend)
                                                    ^              |
                          public tips -> verify -----+              v
                                                  AI brief service (score in code, LLM narrates)
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Show raw frequency, not a risk score, on the map | An officer can verify a count against records; a black-box score cannot be defended in a review. |
| Domain configs (YAML/JSON) drive categories, windows and indicators | Narcotics and crime share one engine; a new domain is a config file, not a code change. |
| Flag rows instead of dropping them | Data-quality problems become visible work items and no incident silently disappears. |
| Compute and explain are separate; the LLM never produces a number | Scores are reproducible and auditable. `explainZone` throws if it is handed a zone without a score. |
| Pluggable LLM provider (`mock` / `ibm_watsonx`) | The brief pipeline runs and is testable with no credentials; the provider is one config switch. |
| Tips are anonymous by design | No name, phone or email is collected, and the tip record stores no client IP. |

## IBM Technologies Used

- **watsonx.ai (text generation):** `src/explain-report-service/src/services/llmProviders/ibmWatsonxProvider.js` implements IBM Cloud IAM token exchange and the watsonx.ai text-generation call, selected with `LLM_PROVIDER=ibm_watsonx`. It was written from IBM's public API documentation and has **not** yet been verified against a live endpoint; the default provider is a deterministic offline mock, which is what the demo and tests exercise.
