#!/usr/bin/env python3
"""
scripts/ingest_cli.py
CLI tool: takes a raw Excel/CSV file and domain config,
and outputs clean, geocoded, deduplicated Incident records matching the platform schemas.

Usage:
    python3 scripts/ingest_cli.py --file data/mock_fir_sample.xlsx --config configs/narcotics.yaml --output clean_incidents.json
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any

# Add parent directory to sys.path so core and server imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import Incident
from core.config_loader import load_domain_config
from core.tabular_parser import parse_tabular_file
from core.geocoder import NominatimGeocoder
from core.deduplicator import detect_duplicates
from core.database import Database

def run_ingestion_pipeline(
    file_path: str,
    config_path: str,
    output_path: Optional[str] = None,
    flagged_output_path: Optional[str] = None,
    store_db: bool = False,
    allow_network: bool = False
) -> Dict[str, Any]:
    print("=" * 70)
    print("CRIME & NARCOTICS INTELLIGENCE DATA INGESTION PIPELINE")
    print("=" * 70)
    print(f"[*] Input File:      {file_path}")
    print(f"[*] Domain Config:   {config_path}")
    
    # 1. Load domain configuration
    domain_config = load_domain_config(config_path)
    print(f"[+] Loaded Config:   domain='{domain_config.domain}', categories={domain_config.categories}")
    print(f"                     indicators={[i['name'] for i in domain_config.indicators]}")

    # 2. Read file bytes
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    file_name = os.path.basename(file_path)

    # 3. Parse tabular file & auto-detect columns & flag rows
    print("\n--- Step 1: Tabular Parsing & Column Auto-Detection ---")
    parsed_data = parse_tabular_file(file_bytes, file_name, domain_config)
    print(f"[+] Detected Columns:")
    for field, col_idx in parsed_data.column_mapping.items():
        if col_idx is not None:
            col_name = parsed_data.headers[col_idx]
            print(f"    - {field:<16} -> '{col_name}' (Col {col_idx + 1})")
        else:
            print(f"    - {field:<16} -> [Not present / inferred]")
            
    print(f"[+] Total rows read:    {parsed_data.metadata['total_rows']}")
    print(f"[+] Confident rows:     {len(parsed_data.valid_rows)}")
    print(f"[!] Flagged rows:       {len(parsed_data.flagged_rows)}")

    # 4. Geocoding
    print("\n--- Step 2: OpenStreetMap Nominatim Geocoding ---")
    cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "geocache.sqlite")
    geocoder = NominatimGeocoder(db_path=cache_path)
    
    incidents_list = []
    for r in parsed_data.valid_rows:
        addr = r["address_text"]
        dist = r.get("district")
        geo = geocoder.geocode(addr, district=dist, allow_network=allow_network)
        
        ind_map = {}
        metric = r.get("indicator_metric")
        if metric is not None:
            if domain_config.domain == "narcotics":
                ind_map["seizure_volume"] = metric
            else:
                ind_map["category_severity"] = metric
                
        inc = Incident(
            domain=domain_config.domain,
            category=r["category"],
            source=r["source"],
            source_ref_id=r.get("source_ref_id"),
            district=r.get("district") or "Unknown",
            police_station=r.get("police_station"),
            lat=geo["lat"],
            lng=geo["lng"],
            address_text=addr,
            occurred_at=r["occurred_at"],
            indicators=ind_map,
            metadata={
                "raw_row_index": r["row_index"],
                "geocoded_source": geo["source"],
                "geocoded_display_name": geo.get("display_name"),
                "raw_data": r["raw_data"]
            }
        )
        incidents_list.append(inc)
        
    print(f"[+] Successfully geocoded {len(incidents_list)} incident locations.")

    # 5. Duplicate Detection
    print("\n--- Step 3: Spatio-Temporal Duplicate Detection ---")
    processed_incidents, dup_pairs = detect_duplicates(incidents_list)
    print(f"[+] Duplicate pairs identified: {len(dup_pairs)}")
    for d in dup_pairs[:5]:
        print(f"    * Canonical [{d['canonical_source'].upper()} {d['canonical_id'][:8]}] <-> "
              f"Duplicate [{d['duplicate_source'].upper()} {d['duplicate_id'][:8]}] "
              f"| {d['distance_meters']}m | {d['time_diff_hours']}h")
    if len(dup_pairs) > 5:
        print(f"    * ... and {len(dup_pairs) - 5} more duplicate pairs.")

    # 6. Database Storage (Optional)
    if store_db:
        db = Database()
        inserted = db.insert_incidents(processed_incidents)
        print(f"\n[+] Stored {inserted} incidents into SQLite database.")

    # 7. Output Result Formatting
    output_records = [inc.to_dict() for inc in processed_incidents]
    
    result = {
        "status": "success",
        "domain": domain_config.domain,
        "input_file": file_name,
        "summary": {
            "total_rows_processed": parsed_data.metadata["total_rows"],
            "clean_incidents_count": len(output_records),
            "flagged_rows_count": len(parsed_data.flagged_rows),
            "duplicate_pairs_identified": len(dup_pairs)
        },
        "incidents": output_records,
        "flagged_rows": parsed_data.flagged_rows,
        "duplicates_summary": dup_pairs
    }

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result["incidents"], f, indent=2)
        print(f"\n[✓] Clean Incident records written to: {output_path}")

    if flagged_output_path:
        os.makedirs(os.path.dirname(os.path.abspath(flagged_output_path)), exist_ok=True)
        with open(flagged_output_path, "w", encoding="utf-8") as f:
            json.dump(result["flagged_rows"], f, indent=2)
        print(f"[✓] Flagged rows written to:            {flagged_output_path}")

    print("\nSample Incident Record Output:")
    if output_records:
        print(json.dumps(output_records[0], indent=2))
        
    print("=" * 70)
    return result

def main():
    parser = argparse.ArgumentParser(description="Ingest law enforcement Excel/CSV logs.")
    parser.add_argument("--file", "-f", required=True, help="Path to input Excel (.xlsx) or CSV file")
    parser.add_argument("--config", "-c", required=True, help="Path to domain config YAML or JSON")
    parser.add_argument("--output", "-o", default=None, help="Output JSON path for clean incidents")
    parser.add_argument("--flagged-output", default=None, help="Output JSON path for flagged rows")
    parser.add_argument("--store-db", action="store_true", help="Store records in SQLite database")
    parser.add_argument("--allow-network", action="store_true", help="Query live Nominatim over internet")

    args = parser.parse_args()
    run_ingestion_pipeline(
        file_path=args.file,
        config_path=args.config,
        output_path=args.output,
        flagged_output_path=args.flagged_output,
        store_db=args.store_db,
        allow_network=args.allow_network
    )

if __name__ == "__main__":
    main()
