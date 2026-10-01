# Source Code

SafeGrid is two cooperating services.

```
src/
  platform/                # Python — ingestion, REST API, dashboard (port 8080)
    core/                  #   tabular parser, geocoder, de-duplicator, indicator/hotspot engine, SQLite layer
    server/                #   REST API (http.server), JWT auth, multipart parser
    frontend/              #   single-page dashboard, upload, tip portal, tip review (Leaflet)
    configs/               #   narcotics / crime domain configs (YAML + JSON)
    data/                  #   synthetic sample datasets (generated DBs are git-ignored)
    scripts/               #   ingest CLI, mock-data generator, end-to-end test suite
    requirements.txt
  explain-report-service/  # Node — LLM-narrated briefs as JSON/PDF (port 4100)
    src/promptTemplates/   #   the one shared, domain-agnostic prompt
    src/services/          #   score bridge, explainService, report builders, LLM providers
    src/pdf/               #   PDF rendering
```

The AI brief service reads the platform's `GET /api/hotspots` using the caller's own JWT.
Both services must share the same `JWT_SECRET`. See [`../docs/setup-guide.md`](../docs/setup-guide.md).

`platform/README.md` and `explain-report-service/README.md` have component-level detail.
