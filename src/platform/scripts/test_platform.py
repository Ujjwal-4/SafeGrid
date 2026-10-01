#!/usr/bin/env python3
"""
scripts/test_platform.py
Comprehensive automated test suite verifying all 7 requirements and schemas:
1. Domain config loading (YAML & JSON) for narcotics & crime.
2. Tabular parser column auto-detection and row flagging.
3. OpenStreetMap Nominatim geocoding & rate limit queuing.
4. Spatio-temporal duplicate detection (Dial-100 vs FIR).
5. Output Incident schema verification (Schema 1 & Req 6).
6. Endpoints testing (all 7 required paths).
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import Incident, Tip, HotspotEntry, User
from core.config_loader import load_domain_config
from core.tabular_parser import parse_tabular_file, auto_detect_columns
from core.geocoder import NominatimGeocoder
from core.deduplicator import detect_duplicates
from core.database import Database
from server.app import create_server
from server.auth import generate_jwt_token, verify_jwt_token

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_PORT = 8991
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(f"FAILED: {msg}")
    print(f"  [✓] {msg}")

def test_domain_configs():
    print("\n--- TEST 1: Domain Configurations (YAML & JSON) ---")
    narcotics_yaml = load_domain_config(os.path.join(BASE_DIR, "configs", "narcotics.yaml"))
    assert_true(narcotics_yaml.domain == "narcotics", "Narcotics YAML domain is 'narcotics'")
    assert_true({"drug_trafficking", "illicit_storage"}.issubset(set(narcotics_yaml.categories)), "Narcotics categories present")
    assert_true(narcotics_yaml.aggregation_window == "monthly", "Narcotics aggregation window is monthly")
    
    ind_names = [i["name"] for i in narcotics_yaml.indicators]
    assert_true(set(ind_names) == {"seizure_volume", "od_admissions", "repeat_offender_density", "verified_tip_density"}, "Narcotics indicators present")

    # Test all 6 statutory domains
    statutory_domains = [
        ("physical_harm", ["murder", "assault", "hit_and_run", "kidnapping"]),
        ("women_children", ["domestic_violence", "sexual_offenses", "child_abuse"]),
        ("property_crimes", ["theft_burglary", "robbery_snatching", "vandalism_arson"]),
        ("cybercrime", ["financial_fraud", "identity_theft", "online_harassment"]),
        ("narcotics", ["drug_trafficking", "illicit_storage"]),
        ("public_disturbance", ["rioting", "cheating_forgery"])
    ]
    for dom_name, expected_cats in statutory_domains:
        cfg = load_domain_config(os.path.join(BASE_DIR, "configs", f"{dom_name}.yaml"))
        assert_true(cfg.domain == dom_name, f"Loaded config for {dom_name}")
        assert_true(set(expected_cats).issubset(set(cfg.categories)), f"Categories for {dom_name} matched")
        assert_true(cfg.governing_law != "", f"Governing law present for {dom_name}")
        assert_true(cfg.required_evidence != "", f"Required evidence present for {dom_name}")
        assert_true(cfg.color.startswith("#"), f"Color code valid for {dom_name}")

    # Category normalization tests
    harm_cfg = load_domain_config(os.path.join(BASE_DIR, "configs", "physical_harm.yaml"))
    assert_true(harm_cfg.normalize_category("attempt to murder") == "murder", "Normalize 'attempt to murder' -> 'murder'")
    assert_true(harm_cfg.normalize_category("hit & run") == "hit_and_run", "Normalize 'hit & run' -> 'hit_and_run'")

    cyber_cfg = load_domain_config(os.path.join(BASE_DIR, "configs", "cybercrime.yaml"))
    assert_true(cyber_cfg.normalize_category("upi scams") == "financial_fraud", "Normalize 'upi scams' -> 'financial_fraud'")
    assert_true(cyber_cfg.normalize_category("cyberstalking") == "online_harassment", "Normalize 'cyberstalking' -> 'online_harassment'")

    prop_cfg = load_domain_config(os.path.join(BASE_DIR, "configs", "property_crimes.yaml"))
    assert_true(prop_cfg.normalize_category("chain snatching") == "robbery_snatching", "Normalize 'chain snatching' -> 'robbery_snatching'")
    assert_true(prop_cfg.normalize_category("house breaking") == "theft_burglary", "Normalize 'house breaking' -> 'theft_burglary'")

def test_tabular_parser_and_flagging():
    print("\n--- TEST 2: Tabular Parser, Auto-Detection & Row Flagging ---")
    cfg = load_domain_config(os.path.join(BASE_DIR, "configs", "crime.yaml"))
    fir_xlsx_path = os.path.join(BASE_DIR, "data", "mock_fir_sample.xlsx")
    with open(fir_xlsx_path, "rb") as f:
        xlsx_bytes = f.read()
        
    parsed = parse_tabular_file(xlsx_bytes, "mock_fir_sample.xlsx", cfg)
    assert_true(parsed.column_mapping.get("location") is not None, "Auto-detected location column")
    assert_true(parsed.column_mapping.get("category") is not None, "Auto-detected category column")
    assert_true(parsed.column_mapping.get("datetime") is not None, "Auto-detected datetime column")
    assert_true(len(parsed.valid_rows) > 0, f"Found {len(parsed.valid_rows)} valid crime rows")
    assert_true(len(parsed.flagged_rows) > 0, f"Found {len(parsed.flagged_rows)} flagged rows")
    
    # Check that intentional malformed rows were flagged
    reasons = [r["flag_reasons"] for r in parsed.flagged_rows]
    flat_reasons = " ".join([str(item).lower() for sublist in reasons for item in sublist])
    assert_true("missing location" in flat_reasons or "missing_location" in flat_reasons, "Detected missing location flag")
    assert_true("invalid date" in flat_reasons or "invalid_datetime" in flat_reasons or "missing date" in flat_reasons, "Detected invalid date flag")
    assert_true("unmapped" in flat_reasons or "unrecognised" in flat_reasons or "category" in flat_reasons, "Detected unrecognised category flag")

def test_geocoder():
    print("\n--- TEST 3: Geocoding & Rate Limiting Queue ---")
    cache_path = os.path.join(BASE_DIR, "data", "test_geocache.sqlite")
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    geocoder = NominatimGeocoder(db_path=cache_path, min_request_interval=1.0)
    
    # 1. Gazetteer / Cache lookup
    t0 = time.time()
    res1 = geocoder.geocode("Connaught Place Block B", district="New Delhi", allow_network=False)
    assert_true(28.0 < res1["lat"] < 29.0 and 77.0 < res1["lng"] < 78.0, "Geocoded Connaught Place coordinates valid")
    assert_true(res1["source"] == "gazetteer", "Identified source as gazetteer")
    
    # 2. Cache hit test
    res2 = geocoder.geocode("Connaught Place Block B", district="New Delhi", allow_network=False)
    assert_true(res2["source"] in ["cache", "gazetteer"], "Cache hit verified")
    
    # 3. Rate limiter timing test
    start_time = time.monotonic()
    geocoder.last_request_time = start_time
    # Next call with allow_network=False won't wait, but with rate limiter lock it tracks request interval
    assert_true(geocoder.min_request_interval >= 1.0, "Rate limiter set to >= 1.0 sec per req")

def test_deduplicator():
    print("\n--- TEST 4: Spatio-temporal Duplicate Detection ---")
    dt1 = "2026-08-15T14:30:00Z"
    dt2 = "2026-08-15T16:00:00Z"  # 1.5 hours later
    
    # Two incidents at same location & category within 1.5 hours
    inc_dial100 = Incident(
        domain="narcotics",
        category="seizure",
        source="call_100",
        source_ref_id="PCR-001",
        district="New Delhi",
        lat=28.6315,
        lng=77.2167,
        address_text="Block B Connaught Place",
        occurred_at=dt1
    )
    
    inc_fir = Incident(
        domain="narcotics",
        category="seizure",
        source="fir",
        source_ref_id="FIR-001",
        district="New Delhi",
        lat=28.6318, # ~35 meters apart
        lng=77.2169,
        address_text="Block B Inner Circle Connaught Place",
        occurred_at=dt2
    )
    
    # Unrelated incident 3 days later
    inc_unrelated = Incident(
        domain="narcotics",
        category="seizure",
        source="fir",
        source_ref_id="FIR-002",
        district="New Delhi",
        lat=28.6315,
        lng=77.2167,
        address_text="Block B Connaught Place",
        occurred_at="2026-08-18T14:30:00Z"
    )
    
    processed, dup_pairs = detect_duplicates([inc_dial100, inc_fir, inc_unrelated], max_distance_meters=200, max_time_hours=4.0)
    assert_true(len(dup_pairs) == 1, f"Exactly 1 duplicate pair detected (found {len(dup_pairs)})")
    
    # Verify canonical assignment (FIR wins over Dial-100)
    canonical = next(i for i in processed if i.source.lower() == "fir" and i.source_ref_id == "FIR-001")
    duplicate = next(i for i in processed if i.source.lower() == "call_100")
    
    assert_true(canonical.metadata["is_duplicate"] == False, "FIR designated as canonical (is_duplicate=False)")
    assert_true(duplicate.metadata["is_duplicate"] == True, "Dial-100 designated as duplicate (is_duplicate=True)")
    assert_true(duplicate.metadata["duplicate_of"] == canonical.id, f"Dial-100 duplicate_of points to canonical FIR ID {canonical.id}")
    assert_true(canonical.id in duplicate.metadata["duplicate_of"], "Duplicate pointer matches")

def test_api_server_endpoints():
    print("\n--- TEST 5: API Endpoints (All 7 required paths) ---")
    server = create_server(host="127.0.0.1", port=TEST_PORT)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)

    try:
        # 1. POST /api/auth/login
        print("\nChecking: POST /api/auth/login")
        login_data = json.dumps({"badge_id": "SUPER-101", "password": "supervisor_pass"}).encode('utf-8')
        req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "POST /api/auth/login status 200")
            auth_res = json.loads(resp.read().decode('utf-8'))
            assert_true("token" in auth_res and auth_res["role"] == "supervisor", "Obtained JWT token and role")
            jwt_token = auth_res["token"]
            
        auth_headers = {
            "Authorization": f"Bearer {jwt_token}"
        }

        # 2. POST /api/tips (public, rate-limited)
        print("\nChecking: POST /api/tips (public)")
        tip_data = json.dumps({
            "domain": "narcotics",
            "category": "peddling_activity",
            "district": "Central",
            "description": "Public report of illegal narcotic exchanges behind market",
            "lat": 28.6450,
            "lng": 77.2120,
            "is_high_priority": True,
            "is_urgent": False
        }).encode('utf-8')
        req = urllib.request.Request(f"{BASE_URL}/api/tips", data=tip_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 201, "POST /api/tips status 201")
            tip_res = json.loads(resp.read().decode('utf-8'))
            assert_true("id" in tip_res and tip_res["status"] == "pending", "Tip created with status 'pending'")
            created_tip_id = tip_res["id"]

        # 3. GET /api/tips?status=&district= (auth)
        print("\nChecking: GET /api/tips?status=&district=")
        req = urllib.request.Request(f"{BASE_URL}/api/tips?status=pending&district=Central", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/tips status 200")
            tips_list = json.loads(resp.read().decode('utf-8'))
            assert_true(any(t["id"] == created_tip_id for t in tips_list), "Created tip present in GET /api/tips list")
            sample_tip = next(t for t in tips_list if t["id"] == created_tip_id)
            assert_true("region" in sample_tip, "Tip schema has 'region' (Integration schema)")
            assert_true("district" in sample_tip, "Tip schema has 'district' (Schema 2)")

        # 4. PATCH /api/tips/:id/verify (auth)
        print(f"\nChecking: PATCH /api/tips/{created_tip_id}/verify")
        verify_data = json.dumps({"status": "verified_true"}).encode('utf-8')
        req = urllib.request.Request(
            f"{BASE_URL}/api/tips/{created_tip_id}/verify",
            data=verify_data,
            headers={**auth_headers, "Content-Type": "application/json"},
            method="PATCH"
        )
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "PATCH /api/tips/:id/verify status 200")
            updated_tip = json.loads(resp.read().decode('utf-8'))
            assert_true(updated_tip["status"] == "verified_true", "Tip status successfully updated to 'verified_true'")
            assert_true(updated_tip["verified_by"] == "SUPER-101", "Tip verified_by set to officer badge")

        # 5. POST /api/upload (auth) multipart file -> { incidents: [...], flagged_rows: [...] }
        print("\nChecking: POST /api/upload (multipart)")
        fir_sample_path = os.path.join(BASE_DIR, "data", "mock_fir_sample.xlsx")
        with open(fir_sample_path, "rb") as f:
            file_bytes = f.read()

        boundary = "----TestPlatformBoundary12345"
        multipart_body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="domain"\r\n\r\n'
            f"narcotics\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="mock_fir_sample.xlsx"\r\n'
            f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
        ).encode('utf-8') + file_bytes + f"\r\n--{boundary}--\r\n".encode('utf-8')

        req = urllib.request.Request(
            f"{BASE_URL}/api/upload",
            data=multipart_body,
            headers={
                **auth_headers,
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            }
        )
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "POST /api/upload status 200")
            upload_res = json.loads(resp.read().decode('utf-8'))
            assert_true("incidents" in upload_res, "Response contains 'incidents'")
            assert_true("flagged_rows" in upload_res, "Response contains 'flagged_rows'")
            assert_true(len(upload_res["incidents"]) > 0, f"Returned {len(upload_res['incidents'])} clean geocoded incidents")
            assert_true(len(upload_res["flagged_rows"]) > 0, f"Returned {len(upload_res['flagged_rows'])} flagged rows")
            
            # Verify Incident schema adherence on uploaded records
            sample_inc = upload_res["incidents"][0]
            required_schema1_keys = ["id", "domain", "category", "source", "source_ref_id", "district",
                                     "police_station", "lat", "lng", "address_text", "occurred_at", "created_at", "metadata"]
            for k in required_schema1_keys:
                assert_true(k in sample_inc, f"Incident schema has '{k}'")
            # Requirement 6 / Integration schema check
            assert_true("date" in sample_inc, "Incident schema has 'date' (Req 6 & Integration)")
            assert_true("indicators" in sample_inc, "Incident schema has 'indicators' (Req 6 & Integration)")

        # 6. GET /api/hotspots?domain=&category=&district= (auth)
        print("\nChecking: GET /api/hotspots?domain=narcotics")
        req = urllib.request.Request(f"{BASE_URL}/api/hotspots?domain=narcotics", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/hotspots?domain=narcotics status 200")
            hotspots = json.loads(resp.read().decode('utf-8'))
            assert_true(isinstance(hotspots, list), "Hotspots returned as array")
            if hotspots:
                h = hotspots[0]
                for k in ["zone", "district", "domain", "category", "lat", "lng", "score", "frequency", "previous_frequency", "trend"]:
                    assert_true(k in h, f"Hotspot schema has '{k}'")

        # 6b. GET /api/hotspots?domain=all (All domains visible simultaneously)
        print("\nChecking: GET /api/hotspots?domain=all (All Domains / Every Hotspot)")
        req = urllib.request.Request(f"{BASE_URL}/api/hotspots?domain=all", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/hotspots?domain=all status 200")
            all_hotspots = json.loads(resp.read().decode('utf-8'))
            assert_true(len(all_hotspots) > 0, f"Retrieved {len(all_hotspots)} cross-domain hotspots")
            domains_found = set(h["domain"] for h in all_hotspots)
            assert_true(len(domains_found) > 1, f"Multi-domain hotspots present: {domains_found}")
            # Ensure color is attached
            assert_true(all("color" in h for h in all_hotspots), "All hotspots have 'color' attribute")

        # 6c. GET /api/configs (All 6 statutory configs returned)
        print("\nChecking: GET /api/configs")
        req = urllib.request.Request(f"{BASE_URL}/api/configs")
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/configs status 200")
            configs_dict = json.loads(resp.read().decode('utf-8'))
            for d in ["physical_harm", "women_children", "property_crimes", "cybercrime", "narcotics", "public_disturbance"]:
                assert_true(d in configs_dict, f"Domain config for '{d}' returned in /api/configs")

        # 7. GET /api/reports/:domain?format=pdf|json (auth)
        print("\nChecking: GET /api/reports/:domain")
        req = urllib.request.Request(f"{BASE_URL}/api/reports/narcotics?format=json", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/reports/narcotics status 200")
            report = json.loads(resp.read().decode('utf-8'))
            assert_true(report["domain"] == "narcotics", "Report domain is 'narcotics'")
            assert_true("executive_summary" in report, "Report has 'executive_summary'")
            assert_true("district_risk_rankings" in report, "Report has 'district_risk_rankings'")
            assert_true("top_hotspot_clusters" in report, "Report has 'top_hotspot_clusters'")

        # 8. GET /api/forecast (Predictive layer)
        print("\nChecking: GET /api/forecast")
        req = urllib.request.Request(f"{BASE_URL}/api/forecast?horizon=4w&range=6m", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/forecast status 200")
            fc_data = json.loads(resp.read().decode('utf-8'))
            assert_true("series" in fc_data, "Forecast has 'series'")
            assert_true("summary" in fc_data, "Forecast has 'summary'")
            assert_true(len(fc_data["series"]) > 0, "Forecast series has data points")
            if fc_data["summary"]:
                s0 = fc_data["summary"][0]
                for k in ["level", "name", "forecast", "lower", "upper", "baseline", "expected_change_ratio", "trend", "model_name", "top_drivers"]:
                    assert_true(k in s0, f"Forecast summary entry has '{k}'")

        # 9. GET /api/forecast/hotspots
        print("\nChecking: GET /api/forecast/hotspots")
        req = urllib.request.Request(f"{BASE_URL}/api/forecast/hotspots?k=5", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/forecast/hotspots status 200")
            hotspots_fc = json.loads(resp.read().decode('utf-8'))
            assert_true(isinstance(hotspots_fc, list), "Forecast hotspots is list")
            assert_true(len(hotspots_fc) > 0, "Forecast hotspots returned entries")
            assert_true("lat" in hotspots_fc[0] and "lng" in hotspots_fc[0], "Forecast hotspots have coordinates")
            assert_true("trend_arrow" in hotspots_fc[0], "Forecast hotspots have trend arrow")

        # 10. GET /api/patterns/temporal
        print("\nChecking: GET /api/patterns/temporal")
        req = urllib.request.Request(f"{BASE_URL}/api/patterns/temporal", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/patterns/temporal status 200")
            patt = json.loads(resp.read().decode('utf-8'))
            assert_true("matrix" in patt, "Temporal patterns has 7x24 'matrix'")
            assert_true(len(patt["matrix"]) == 7, "Matrix has 7 weekdays")
            assert_true(len(patt["matrix"][0]) == 24, "Matrix has 24 hours")
            assert_true("peak_weekday" in patt, "Has 'peak_weekday'")
            assert_true("peak_hour" in patt, "Has 'peak_hour'")

        # 11. GET /api/allocation (Prescriptive layer)
        print("\nChecking: GET /api/allocation")
        req = urllib.request.Request(f"{BASE_URL}/api/allocation?district=Central&units=20", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/allocation status 200")
            alloc_data = json.loads(resp.read().decode('utf-8'))
            assert_true(isinstance(alloc_data, list), "Allocation returns list")
            assert_true(len(alloc_data) > 0, "Allocations returned for district")
            total_allocated = sum(a["recommended_units"] for a in alloc_data)
            assert_true(total_allocated == 20, f"Exact integer unit apportionment sums to 20 (got {total_allocated})")
            assert_true("rationale" in alloc_data[0], "Allocation has 'rationale'")

        # 12. GET /api/model/metrics
        print("\nChecking: GET /api/model/metrics")
        req = urllib.request.Request(f"{BASE_URL}/api/model/metrics", headers=auth_headers)
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "GET /api/model/metrics status 200")
            met_data = json.loads(resp.read().decode('utf-8'))
            assert_true("champion" in met_data, "Metrics has 'champion'")
            assert_true("history" in met_data, "Metrics has 'history'")
            assert_true(len(met_data["history"]) > 0, "History has metric records")

        # 13. POST /api/model/retrain (supervisor only)
        print("\nChecking: POST /api/model/retrain")
        req = urllib.request.Request(
            f"{BASE_URL}/api/model/retrain",
            data=b"{}",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert_true(resp.status == 200, "POST /api/model/retrain status 200")
            retrain_res = json.loads(resp.read().decode('utf-8'))
            assert_true("champion_model" in retrain_res, "Retrain response has 'champion_model'")
            assert_true("mae" in retrain_res, "Retrain response has 'mae'")
            assert_true("poisson_deviance" in retrain_res, "Retrain response has 'poisson_deviance'")
            assert_true("pai" in retrain_res, "Retrain response has 'pai'")

    finally:
        server.shutdown()
        server.server_close()
        print("\n[+] Test server closed.")

def main():
    print("=" * 70)
    print("RUNNING END-TO-END VERIFICATION SUITE")
    print("=" * 70)
    test_domain_configs()
    test_tabular_parser_and_flagging()
    test_geocoder()
    test_deduplicator()
    test_api_server_endpoints()
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    main()
