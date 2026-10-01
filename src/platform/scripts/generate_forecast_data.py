#!/usr/bin/env python3
"""
scripts/generate_forecast_data.py
Generates 3 full years of realistic incidents for SafeGrid's Predictive & Prescriptive layer:
- 3 States (Delhi NCT, Haryana, Uttar Pradesh)
- 10 Districts
- 30 Zones
- Categories: narcotics, theft, hit_and_run, assault, burglary
- Incorporates per-zone base rates, upward trend, annual seasonality, festival surges,
  weekday/hour patterns, near-repeat clusters, and Cyber City emerging hotspot.
- Outputs matching upload CSV format.
"""

import os
import sys
import csv
import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.synthetic_forecast_generator import generate_synthetic_incidents
from core.database import Database
from core.models import Incident
from core.predictive_coordinator import PredictiveCoordinator

def main():
    print("[*] Generating 3-year synthetic incident dataset across 3 states / 10 districts / 30 zones...")
    start_date = datetime.date(2023, 10, 1)
    end_date = datetime.date(2026, 9, 28)
    
    incidents = generate_synthetic_incidents(start_date=start_date, end_date=end_date, seed=42)
    print(f"[+] Successfully generated {len(incidents)} incidents across 3 years.")

    # Write CSV
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "mock_synthetic_3yr_incidents.csv")
    
    fieldnames = [
        "source", "source_ref_id", "district", "police_station",
        "crime_type", "address_text", "lat", "lng", "occurred_at", "remarks"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for inc in incidents:
            writer.writerow(inc)
    print(f"[+] Saved synthetic CSV dataset to: {csv_path}")

    # Seed platform database
    db_path = os.path.join(data_dir, "platform.sqlite")
    db = Database(db_path)
    
    print("[*] Seeding database with 3-year incidents...")
    domain_map = {
        "theft": "property_crimes",
        "burglary": "property_crimes",
        "assault": "physical_harm",
        "hit_and_run": "physical_harm",
        "narcotics": "narcotics"
    }

    inc_models = []
    for inc in incidents:
        c_type = inc["crime_type"]
        dom = domain_map.get(c_type, "crime")
        inc_models.append(Incident(
            domain=dom,
            category=c_type,
            source=inc["source"],
            source_ref_id=inc["source_ref_id"],
            district=inc["district"],
            police_station=inc["police_station"],
            lat=inc["lat"],
            lng=inc["lng"],
            address_text=inc["address_text"],
            occurred_at=inc["occurred_at"]
        ))

    inserted = db.insert_incidents(inc_models)
    print(f"[+] Successfully inserted {inserted} incidents into database.")

    # Initialize and train coordinator
    print("[*] Initializing Predictive Coordinator and training ensemble models...")
    coord = PredictiveCoordinator(db)
    retrain_res = coord.retrain_models()
    print(f"[+] Model Training Complete! Champion: {retrain_res['champion_model']}, MAE: {retrain_res['mae']}, Poisson Deviance: {retrain_res['poisson_deviance']}, PAI: {retrain_res['pai']}")

if __name__ == "__main__":
    main()
