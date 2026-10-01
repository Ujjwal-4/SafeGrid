"""
server/app.py
Production-ready REST API server for the crime/narcotics intelligence platform.
Exposes exact paths:
POST   /api/auth/login              body: { badge_id, password }           -> { token, role }
POST   /api/upload                  (auth)  multipart file                 -> { incidents: [...], flagged_rows: [...] }
POST   /api/tips                    (public, rate-limited)                 -> { id, status: "pending" }
GET    /api/tips?status=&district=  (auth)                                 -> Tip[]
PATCH  /api/tips/:id/verify         (auth)  body: { status }                -> updated Tip
GET    /api/hotspots?domain=&category=&district=  (auth)                  -> HotspotEntry[]
GET    /api/reports/:domain         (auth)  ?format=pdf|json                -> report
GET    /                            (web ui)                               -> Interactive Web Dashboard
"""

import os
import sys
import re
import json
import time
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Optional

# Ensure project root is in sys.path so 'core' and 'server' can be imported directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import Incident, Tip
from core.database import Database
from core.config_loader import load_domain_config, DomainConfig
from core.tabular_parser import parse_tabular_file
from core.geocoder import NominatimGeocoder
from core.deduplicator import detect_duplicates
from core.indicator_engine import calculate_district_indicators, compute_hotspots, generate_domain_report
from core.predictive_coordinator import PredictiveCoordinator
from server.auth import authenticate_officer, generate_jwt_token, extract_auth_claims
from server.multipart_parser import parse_multipart_form_data

# Rate limiting for public tips endpoint: IP -> list of request timestamps
PUBLIC_RATE_LIMIT_STORE: Dict[str, list] = {}
RATE_LIMIT_WINDOW = 60.0  # seconds
MAX_REQUESTS_PER_WINDOW = 15

CONFIGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class IntelPlatformRequestHandler(BaseHTTPRequestHandler):
    db = Database()
    geocoder = NominatimGeocoder()
    predictive_coord = PredictiveCoordinator(db)
    
    # Dynamically load all domain configs from CONFIGS_DIR
    domain_configs: Dict[str, DomainConfig] = {}
    if os.path.exists(CONFIGS_DIR):
        for _fname in sorted(os.listdir(CONFIGS_DIR)):
            if _fname.endswith(".yaml") or _fname.endswith(".yml"):
                try:
                    _c = load_domain_config(os.path.join(CONFIGS_DIR, _fname))
                    domain_configs[_c.domain] = _c
                except Exception as _e:
                    pass

    def _send_json(self, status_code: int, data: Any):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, html_str: str):
        body = html_str.encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: str, content_type: str, status_code: int = 200):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(status_code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self._send_error(404, "File not found")

    def _send_error(self, status_code: int, message: str):
        self._send_json(status_code, {"error": message, "status": status_code})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _read_body_bytes(self) -> bytes:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return b''

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        raw = self._read_body_bytes()
        if not raw:
            return None
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return None

    def _check_rate_limit(self, client_ip: str) -> bool:
        now = time.time()
        timestamps = PUBLIC_RATE_LIMIT_STORE.get(client_ip, [])
        # Prune old
        valid_ts = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        if len(valid_ts) >= MAX_REQUESTS_PER_WINDOW:
            PUBLIC_RATE_LIMIT_STORE[client_ip] = valid_ts
            return False
        valid_ts.append(now)
        PUBLIC_RATE_LIMIT_STORE[client_ip] = valid_ts
        return True

    def _require_auth(self) -> Optional[Dict[str, Any]]:
        claims = extract_auth_claims(self.headers)
        if not claims:
            self._send_error(401, "Unauthorized: Valid Bearer JWT token required in Authorization header")
            return None
        return claims

    # ------------------ GET ROUTING ------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Static Files & Frontend UI Routes
        if path.startswith("/css/"):
            rel_path = path[5:]
            local_path = os.path.join(FRONTEND_DIR, "css", rel_path)
            if os.path.exists(local_path):
                self._send_file(local_path, "text/css; charset=utf-8")
                return

        if path.startswith("/js/"):
            rel_path = path[4:]
            local_path = os.path.join(FRONTEND_DIR, "js", rel_path)
            if os.path.exists(local_path):
                self._send_file(local_path, "application/javascript; charset=utf-8")
                return

        if path in ["/", "/dashboard", "/signin", "/upload", "/tips-portal", "/tips-review"]:
            self._handle_dashboard()
            return

        # 2. GET /api/tips?status=&district=&region= (auth)
        if path == "/api/tips":
            claims = self._require_auth()
            if not claims:
                return
            status = query.get("status", [None])[0]
            district = query.get("district", [None])[0]
            region = query.get("region", [None])[0]
            tips = self.db.get_tips(status=status, district=district, region=region)
            self._send_json(200, tips)
            return

        # 3. GET /api/hotspots?domain=&category=&district=&zone= (auth)
        if path == "/api/hotspots":
            claims = self._require_auth()
            if not claims:
                return
            domain_param = query.get("domain", ["all"])[0].lower() if query.get("domain") else "all"
            category = query.get("category", [None])[0]
            district = query.get("district", [None])[0] or query.get("zone", [None])[0]

            if category and category.lower() in ["all", "", "none"]:
                category = None
            if district and district.lower() in ["all", "", "none"]:
                district = None

            if domain_param in ["all", "", "none"]:
                incidents = self.db.get_incidents(domain=None, district=district, category=category)
                hotspots = compute_hotspots(incidents, domain_config=None, filter_district=district, filter_category=category)
                self._send_json(200, [h.to_dict() for h in hotspots])
                return

            if domain_param not in self.domain_configs:
                valid_domains = list(self.domain_configs.keys()) + ["all"]
                self._send_error(400, f"Unsupported domain '{domain_param}'. Valid domains: {valid_domains}")
                return

            cfg = self.domain_configs[domain_param]
            incidents = self.db.get_incidents(domain=domain_param, district=district, category=category)
            hotspots = compute_hotspots(incidents, domain_config=cfg, filter_district=district, filter_category=category)
            self._send_json(200, [h.to_dict() for h in hotspots])
            return

        # 4. GET /api/reports/:domain?format=pdf|json (auth)
        match_report = re.match(r"^/api/reports/([a-zA-Z0-9_-]+)$", path)
        if match_report:
            claims = self._require_auth()
            if not claims:
                return
            domain = match_report.group(1).lower()
            if domain not in self.domain_configs:
                self._send_error(404, f"Domain config for '{domain}' not found")
                return

            fmt = query.get("format", ["json"])[0].lower()
            cfg = self.domain_configs[domain]
            incidents = self.db.get_incidents(domain=domain)
            raw_tips = self.db.get_tips()
            tips = [Tip(**t) for t in raw_tips]

            report_data = generate_domain_report(cfg, incidents, tips, format=fmt)
            self._send_json(200, report_data)
            return

        # 5. GET /api/configs (utility: inspection of configs)
        if path == "/api/configs":
            self._send_json(200, {k: v.to_dict() for k, v in self.domain_configs.items()})
            return

        # 6. GET /api/forecast (auth: officer=own district, supervisor=own state/all)
        if path == "/api/forecast":
            claims = self._require_auth()
            if not claims:
                return
            category = query.get("category", [None])[0]
            level = query.get("level", ["zone"])[0]
            state = query.get("state", [None])[0]
            district = query.get("district", [None])[0]
            zone = query.get("zone", [None])[0]
            horizon = query.get("horizon", ["4w"])[0]
            range_val = query.get("range", ["1y"])[0]
            per_capita = query.get("per_capita", ["false"])[0].lower() in ["true", "1", "yes"]

            user_role = claims.get("role", "officer")
            user_dist = claims.get("district")
            if user_role == "officer" and user_dist:
                district = user_dist

            fc = self.predictive_coord.get_forecast(
                category=category,
                level=level,
                state=state,
                district=district,
                zone=zone,
                horizon=horizon,
                range_filter=range_val,
                per_capita=per_capita
            )
            self._send_json(200, fc)
            return

        # 7. GET /api/forecast/hotspots (auth)
        if path == "/api/forecast/hotspots":
            claims = self._require_auth()
            if not claims:
                return
            category = query.get("category", [None])[0]
            level = query.get("level", ["zone"])[0]
            horizon = query.get("horizon", ["4w"])[0]
            state = query.get("state", [None])[0]
            district = query.get("district", [None])[0]
            try:
                k = int(query.get("k", [10])[0])
            except ValueError:
                k = 10

            user_role = claims.get("role", "officer")
            user_dist = claims.get("district")
            if user_role == "officer" and user_dist:
                district = user_dist

            hotspots = self.predictive_coord.get_forecast_hotspots(
                category=category,
                level=level,
                horizon=horizon,
                k=k,
                state=state,
                district=district
            )
            self._send_json(200, hotspots)
            return

        # 8. GET /api/patterns/temporal (auth)
        if path == "/api/patterns/temporal":
            claims = self._require_auth()
            if not claims:
                return
            zone = query.get("zone", [None])[0]
            category = query.get("category", [None])[0]
            district = query.get("district", [None])[0]

            user_role = claims.get("role", "officer")
            user_dist = claims.get("district")
            if user_role == "officer" and user_dist:
                district = user_dist

            patterns = self.predictive_coord.get_temporal_patterns(
                zone=zone,
                category=category,
                district=district
            )
            self._send_json(200, patterns)
            return

        # 9. GET /api/allocation (auth)
        if path == "/api/allocation":
            claims = self._require_auth()
            if not claims:
                return
            district = query.get("district", [None])[0]
            horizon = query.get("horizon", ["4w"])[0]
            try:
                units = int(query.get("units", [20])[0])
            except ValueError:
                units = 20

            user_role = claims.get("role", "officer")
            user_dist = claims.get("district")
            if user_role == "officer" and user_dist:
                district = user_dist

            alloc = self.predictive_coord.get_patrol_allocation(
                district=district,
                units=units,
                horizon=horizon
            )
            self._send_json(200, alloc)
            return

        # 10. GET /api/model/metrics (auth)
        if path == "/api/model/metrics":
            claims = self._require_auth()
            if not claims:
                return
            metrics_history = self.db.get_model_metrics(limit=50)
            champ = metrics_history[0]["champion_model"] if metrics_history else self.predictive_coord.ensemble.champion_name
            self._send_json(200, {
                "champion": champ,
                "history": metrics_history
            })
            return

        self._send_error(404, f"Endpoint not found: GET {path}")

    # ------------------ POST ROUTING ------------------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. POST /api/auth/login
        if path == "/api/auth/login":
            body = self._read_json_body()
            if not body or "badge_id" not in body or "password" not in body:
                self._send_error(400, "Missing required fields: badge_id, password")
                return
            user = authenticate_officer(self.db, body["badge_id"], body["password"])
            if not user:
                self._send_error(401, "Invalid badge ID or password")
                return
            token = generate_jwt_token(user)
            self._send_json(200, {
                "token": token,
                "role": user["role"],
                "badge_id": user["badge_id"],
                "name": user["name"]
            })
            return

        # 2. POST /api/upload (auth) multipart file -> { incidents: [...], flagged_rows: [...] }
        if path == "/api/upload":
            claims = self._require_auth()
            if not claims:
                return

            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_error(400, "Expected multipart/form-data with file upload")
                return

            raw_body = self._read_body_bytes()
            fields, files = parse_multipart_form_data(raw_body, content_type)

            if not files:
                self._send_error(400, "No file uploaded. Expected form field with file")
                return

            # Take first file
            file_key = list(files.keys())[0]
            filename, file_bytes = files[file_key]

            # Domain selection (from form field, filename heuristic, or auto-detect from content)
            domain_name = fields.get("domain", "").lower()
            if not domain_name or domain_name not in self.domain_configs:
                fn_lower = filename.lower()
                if any(k in fn_lower for k in ["physical", "harm", "murder", "assault", "violence"]):
                    domain_name = "physical_harm"
                elif any(k in fn_lower for k in ["women", "child", "pocso", "domestic"]):
                    domain_name = "women_children"
                elif any(k in fn_lower for k in ["property", "theft", "burglary", "robbery"]):
                    domain_name = "property_crimes"
                elif any(k in fn_lower for k in ["cyber", "1930", "phishing", "fraud", "scam"]):
                    domain_name = "cybercrime"
                elif any(k in fn_lower for k in ["narcotic", "drug", "seizure", "ndps"]):
                    domain_name = "narcotics"
                elif any(k in fn_lower for k in ["public", "disturbance", "riot", "cheating"]):
                    domain_name = "public_disturbance"
                elif "crime" in fn_lower or "fir" in fn_lower or "dial" in fn_lower:
                    domain_name = "physical_harm" if "physical_harm" in self.domain_configs else "crime"
                else:
                    default_dom = "physical_harm" if "physical_harm" in self.domain_configs else list(self.domain_configs.keys())[0]
                    domain_name = default_dom

            cfg = self.domain_configs.get(domain_name, list(self.domain_configs.values())[0])

            # Parse tabular file (CSV or XLSX)
            parsed_data = parse_tabular_file(file_bytes, filename, cfg)

            # Requirement 4: If lat and lng are present and valid, use them and SKIP geocoding!
            incidents_to_dedup = []
            final_flagged_rows = list(parsed_data.flagged_rows)

            for row in parsed_data.valid_rows:
                addr = row["address_text"]
                dist = row.get("district")
                row_domain = row.get("domain") or cfg.domain

                if row.get("lat") is not None and row.get("lng") is not None:
                    # Valid coordinates already in file: USE THEM AND SKIP GEOCODING!
                    final_lat = float(row["lat"])
                    final_lng = float(row["lng"])
                    geo_source = "file_coordinates"
                else:
                    # Only geocode rows with address_text but no coordinates
                    geo_res = self.geocoder.geocode(addr, district=dist, allow_network=True)
                    if (geo_res and geo_res.get("lat") is not None and geo_res.get("lng") is not None 
                            and geo_res.get("source") != "failed"):
                        final_lat = float(geo_res["lat"])
                        final_lng = float(geo_res["lng"])
                        geo_source = geo_res.get("source", "geocoded")
                    else:
                        # Geocoding failure flags that one row only, with reason "geocoding failed"
                        final_flagged_rows.append({
                            "row_index": row["row_index"],
                            "flag_reason": "geocoding failed",
                            "flag_reasons": ["geocoding failed"],
                            "confidence_score": 0.0,
                            "raw_data": row["raw_data"],
                            "partial_mapping": {
                                "address_text": addr,
                                "category": row["category"],
                                "occurred_at": row["occurred_at"],
                                "district": dist,
                                "source": row.get("source", "")
                            }
                        })
                        continue

                # Indicator metric extraction
                ind_map = {}
                metric_val = row.get("indicator_metric")
                if metric_val is not None:
                    if row_domain == "narcotics":
                        ind_map["seizure_volume"] = metric_val
                    else:
                        ind_map["category_severity"] = metric_val

                inc = Incident(
                    domain=row_domain,
                    category=row["category"],
                    source=row["source"],
                    source_ref_id=row.get("source_ref_id"),
                    district=row.get("district") or "Unknown",
                    police_station=row.get("police_station"),
                    lat=final_lat,
                    lng=final_lng,
                    address_text=addr,
                    occurred_at=row["occurred_at"],
                    indicators=ind_map,
                    metadata={
                        "raw_row_index": row["row_index"],
                        "geocoded_source": geo_source,
                        "raw_data": row["raw_data"]
                    }
                )
                incidents_to_dedup.append(inc)

            # Spatio-temporal duplicate detection
            processed_incidents, dup_pairs = detect_duplicates(incidents_to_dedup)

            # Insert into database
            if processed_incidents:
                self.db.insert_incidents(processed_incidents)
                # Auto-trigger walk-forward model retraining asynchronously after upload
                threading.Thread(target=self.predictive_coord.retrain_models, daemon=True).start()

            # Sort flagged rows by row index
            final_flagged_rows.sort(key=lambda x: x.get("row_index", 0))

            # Calculate flagged_by_reason breakdown
            flagged_by_reason = {}
            for r in final_flagged_rows:
                reasons = r.get("flag_reasons") or [r.get("flag_reason", "unspecified")]
                for reason in reasons:
                    flagged_by_reason[reason] = flagged_by_reason.get(reason, 0) + 1

            # Requirement 6: Console/log summary
            total_rows_read = parsed_data.metadata.get("total_rows", len(processed_incidents) + len(final_flagged_rows))
            print("\n" + "=" * 60, flush=True)
            print(f"[INGESTION SUMMARY] File: {filename}", flush=True)
            print(f"  Rows read:                 {total_rows_read}", flush=True)
            print(f"  Valid incidents:           {len(processed_incidents)}", flush=True)
            print(f"  Flagged rows:              {len(final_flagged_rows)}", flush=True)
            if flagged_by_reason:
                print(f"  Flagged by reason:", flush=True)
                for reason, count in sorted(flagged_by_reason.items(), key=lambda x: -x[1]):
                    print(f"    - {reason}: {count}", flush=True)
            print(f"  Duplicate pairs detected:  {len(dup_pairs)}", flush=True)
            print("=" * 60 + "\n", flush=True)

            # Build response matching { incidents: [...], flagged_rows: [...] }
            response_payload = {
                "summary": {
                    "total_rows_processed": total_rows_read,
                    "valid_incidents": len(processed_incidents),
                    "flagged_rows_count": len(final_flagged_rows),
                    "duplicate_pairs_identified": len(dup_pairs),
                    "domain": cfg.domain,
                    "file_name": filename,
                    "flagged_by_reason": flagged_by_reason
                },
                "incidents": [inc.to_dict() for inc in processed_incidents],
                "flagged_rows": final_flagged_rows,
                "duplicates_summary": dup_pairs
            }
            self._send_json(200, response_payload)
            return

        # 3. POST /api/tips (public, rate-limited) -> { id, status: "pending" }
        if path == "/api/tips":
            client_ip = self.client_address[0]
            if not self._check_rate_limit(client_ip):
                self._send_error(429, "Rate limit exceeded. Maximum 15 tips per minute from this IP.")
                return

            body = self._read_json_body()
            if not body:
                self._send_error(400, "Invalid JSON body")
                return

            domain = str(body.get("domain", "narcotics")).lower()
            category = str(body.get("category", "")).lower()
            region = str(body.get("region") or body.get("district") or "Unknown")
            description = str(body.get("description", ""))

            if not category or not description:
                self._send_error(400, "Missing required fields: category, description")
                return

            # Normalize category if valid domain
            if domain in self.domain_configs:
                norm_cat = self.domain_configs[domain].normalize_category(category)
                if norm_cat:
                    category = norm_cat

            tip = Tip(
                domain=domain,
                category=category,
                region=region,
                district=region,
                description=description,
                photo_url=body.get("photo_url"),
                lat=body.get("lat"),
                lng=body.get("lng"),
                is_high_priority=body.get("is_high_priority", False),
                is_urgent=body.get("is_urgent", False),
                status="pending"
            )

            tip_id = self.db.insert_tip(tip)
            self._send_json(201, {"id": tip_id, "status": "pending"})
            return

        # 4. POST /api/model/retrain (auto-triggered or supervisor-only manual trigger)
        if path == "/api/model/retrain":
            claims = self._require_auth()
            if not claims:
                return
            if claims.get("role") != "supervisor":
                self._send_error(403, "Forbidden: Only supervisor can manually trigger model retraining")
                return

            res = self.predictive_coord.retrain_models(user_badge=claims.get("badge_id"))
            self._send_json(200, res)
            return

        self._send_error(404, f"Endpoint not found: POST {path}")

    # ------------------ PATCH ROUTING ------------------
    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # PATCH /api/tips/:id/verify (auth) body: { status } -> updated Tip
        match_verify = re.match(r"^/api/tips/([a-zA-Z0-9_-]+)/verify$", path)
        if match_verify:
            claims = self._require_auth()
            if not claims:
                return

            tip_id = match_verify.group(1)
            body = self._read_json_body()
            if not body or "status" not in body:
                self._send_error(400, "Missing required field: status ('verified_true' or 'verified_false')")
                return

            new_status = str(body["status"]).lower()
            if new_status not in ["verified_true", "verified_false", "pending"]:
                self._send_error(400, "status must be 'verified_true' or 'verified_false'")
                return

            verified_by = claims.get("badge_id") or claims.get("sub")
            verified_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            updated_tip = self.db.update_tip_status(tip_id, new_status, verified_by, verified_at)
            if not updated_tip:
                self._send_error(404, f"Tip with id '{tip_id}' not found")
                return

            self._send_json(200, updated_tip)
            return

        self._send_error(404, f"Endpoint not found: PATCH {path}")

    def _handle_dashboard(self):
        """Serves the complete frontend user interface."""
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            self._send_file(index_file, "text/html; charset=utf-8")
        else:
            self._send_html(200, "<h1>Crime & Narcotics Intelligence Platform</h1><p>Frontend file missing.</p>")

def create_server(host: str = "0.0.0.0", port: int = 8080) -> ThreadedHTTPServer:
    server = ThreadedHTTPServer((host, port), IntelPlatformRequestHandler)
    return server

def run_server(host: str = "0.0.0.0", port: int = 8080):
    server = create_server(host, port)
    print(f"Server started on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Server stopped.")

if __name__ == "__main__":
    run_server()
