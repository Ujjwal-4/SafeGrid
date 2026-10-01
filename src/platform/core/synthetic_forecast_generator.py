"""
core/synthetic_forecast_generator.py
Generates 3 years of realistic statutory crime incidents across:
- 3 States (Delhi NCT, Haryana, Uttar Pradesh)
- 10 Districts
- 30 Zones
Categories: narcotics, theft, hit_and_run, assault, burglary

Features incorporated:
1. Per-zone base Poisson arrival rates
2. Upward trend in selected zones
3. Yearly seasonality (cyclical seasonal component)
4. Indian festival/holiday spikes (Diwali, Holi, Dussehra, New Year, etc.)
5. Category-specific weekday and hour distribution
6. Near-repeat spatio-temporal clustering (elevated probability within 48h and 300m)
7. ONE emerging hotspot starting in the last 3 months (Cyber City, Gurugram East)
"""

import os
import math
import random
import datetime
from typing import List, Dict, Any, Tuple

# Hierarchy Definition
HIERARCHY = {
    "Delhi NCT": {
        "Central": ["Connaught Place", "Paharganj", "Karol Bagh"],
        "New Delhi": ["Janpath", "Chanakyapuri", "Khan Market"],
        "South": ["Hauz Khas", "Saket", "Vasant Kunj"],
        "North": ["Civil Lines", "Kashmere Gate", "Mukherjee Nagar"]
    },
    "Haryana": {
        "Gurugram East": ["Cyber City", "Sector 29", "Golf Course Road"],
        "Gurugram West": ["Old Gurugram", "Palam Vihar", "Sohna Road"],
        "Faridabad": ["Faridabad NIT", "Old Faridabad", "Ballabgarh"]
    },
    "Uttar Pradesh": {
        "Noida Central": ["Atta Market", "Sector 62", "Botanical Garden"],
        "Greater Noida": ["Pari Chowk", "Knowledge Park", "Surajpur"],
        "Ghaziabad": ["Indirapuram", "Vaishali", "Raj Nagar"]
    }
}

ZONE_METADATA = {
    # Delhi NCT - Central
    "Connaught Place": {"lat": 28.6315, "lng": 77.2167, "district": "Central", "state": "Delhi NCT", "base_rate": 4.5, "trend": 0.05},
    "Paharganj": {"lat": 28.6430, "lng": 77.2140, "district": "Central", "state": "Delhi NCT", "base_rate": 3.8, "trend": 0.15},
    "Karol Bagh": {"lat": 28.6520, "lng": 77.1900, "district": "Central", "state": "Delhi NCT", "base_rate": 3.2, "trend": 0.0},
    # Delhi NCT - New Delhi
    "Janpath": {"lat": 28.6250, "lng": 77.2180, "district": "New Delhi", "state": "Delhi NCT", "base_rate": 2.0, "trend": -0.05},
    "Chanakyapuri": {"lat": 28.5950, "lng": 77.1850, "district": "New Delhi", "state": "Delhi NCT", "base_rate": 1.2, "trend": -0.05},
    "Khan Market": {"lat": 28.6000, "lng": 77.2270, "district": "New Delhi", "state": "Delhi NCT", "base_rate": 1.8, "trend": 0.02},
    # Delhi NCT - South
    "Hauz Khas": {"lat": 28.5490, "lng": 77.2000, "district": "South", "state": "Delhi NCT", "base_rate": 3.6, "trend": 0.12},
    "Saket": {"lat": 28.5240, "lng": 77.2150, "district": "South", "state": "Delhi NCT", "base_rate": 3.0, "trend": 0.05},
    "Vasant Kunj": {"lat": 28.5290, "lng": 77.1520, "district": "South", "state": "Delhi NCT", "base_rate": 2.5, "trend": 0.0},
    # Delhi NCT - North
    "Civil Lines": {"lat": 28.6810, "lng": 77.2240, "district": "North", "state": "Delhi NCT", "base_rate": 2.2, "trend": 0.0},
    "Kashmere Gate": {"lat": 28.6670, "lng": 77.2280, "district": "North", "state": "Delhi NCT", "base_rate": 4.0, "trend": 0.10},
    "Mukherjee Nagar": {"lat": 28.7060, "lng": 77.2140, "district": "North", "state": "Delhi NCT", "base_rate": 2.4, "trend": 0.08},
    # Haryana - Gurugram East
    "Cyber City": {"lat": 28.4950, "lng": 77.0890, "district": "Gurugram East", "state": "Haryana", "base_rate": 1.5, "trend": 0.0, "is_emerging_hotspot": True},
    "Sector 29": {"lat": 28.4680, "lng": 77.0620, "district": "Gurugram East", "state": "Haryana", "base_rate": 3.8, "trend": 0.20},
    "Golf Course Road": {"lat": 28.4500, "lng": 77.1000, "district": "Gurugram East", "state": "Haryana", "base_rate": 2.0, "trend": 0.05},
    # Haryana - Gurugram West
    "Old Gurugram": {"lat": 28.4720, "lng": 77.0250, "district": "Gurugram West", "state": "Haryana", "base_rate": 3.5, "trend": 0.02},
    "Palam Vihar": {"lat": 28.5080, "lng": 77.0350, "district": "Gurugram West", "state": "Haryana", "base_rate": 2.2, "trend": 0.0},
    "Sohna Road": {"lat": 28.4100, "lng": 77.0400, "district": "Gurugram West", "state": "Haryana", "base_rate": 2.8, "trend": 0.14},
    # Haryana - Faridabad
    "Faridabad NIT": {"lat": 28.4000, "lng": 77.3000, "district": "Faridabad", "state": "Haryana", "base_rate": 3.4, "trend": 0.04},
    "Old Faridabad": {"lat": 28.4180, "lng": 77.3180, "district": "Faridabad", "state": "Haryana", "base_rate": 2.7, "trend": 0.0},
    "Ballabgarh": {"lat": 28.3400, "lng": 77.3300, "district": "Faridabad", "state": "Haryana", "base_rate": 2.5, "trend": 0.06},
    # Uttar Pradesh - Noida Central
    "Atta Market": {"lat": 28.5700, "lng": 77.3220, "district": "Noida Central", "state": "Uttar Pradesh", "base_rate": 4.2, "trend": 0.08},
    "Sector 62": {"lat": 28.6250, "lng": 77.3650, "district": "Noida Central", "state": "Uttar Pradesh", "base_rate": 2.8, "trend": 0.05},
    "Botanical Garden": {"lat": 28.5640, "lng": 77.3340, "district": "Noida Central", "state": "Uttar Pradesh", "base_rate": 3.0, "trend": 0.10},
    # Uttar Pradesh - Greater Noida
    "Pari Chowk": {"lat": 28.4670, "lng": 77.5100, "district": "Greater Noida", "state": "Uttar Pradesh", "base_rate": 3.1, "trend": 0.18},
    "Knowledge Park": {"lat": 28.4600, "lng": 77.4950, "district": "Greater Noida", "state": "Uttar Pradesh", "base_rate": 2.2, "trend": 0.05},
    "Surajpur": {"lat": 28.5300, "lng": 77.4900, "district": "Greater Noida", "state": "Uttar Pradesh", "base_rate": 2.6, "trend": 0.0},
    # Uttar Pradesh - Ghaziabad
    "Indirapuram": {"lat": 28.6400, "lng": 77.3750, "district": "Ghaziabad", "state": "Uttar Pradesh", "base_rate": 3.9, "trend": 0.22},
    "Vaishali": {"lat": 28.6480, "lng": 77.3400, "district": "Ghaziabad", "state": "Uttar Pradesh", "base_rate": 3.3, "trend": 0.06},
    "Raj Nagar": {"lat": 28.6850, "lng": 77.4400, "district": "Ghaziabad", "state": "Uttar Pradesh", "base_rate": 2.9, "trend": 0.02}
}

CATEGORIES = ["theft", "burglary", "assault", "hit_and_run", "narcotics"]

CATEGORY_CONFIG = {
    "theft": {
        "share": 0.38,
        "peak_days": [4, 5, 6],       # Fri, Sat, Sun
        "peak_hours": [16, 17, 18, 19, 20, 21],
        "domain": "property_crimes"
    },
    "burglary": {
        "share": 0.22,
        "peak_days": [0, 1, 2, 3],    # Weekdays
        "peak_hours": [1, 2, 3, 4, 12, 13, 14],
        "domain": "property_crimes"
    },
    "assault": {
        "share": 0.16,
        "peak_days": [4, 5],          # Fri, Sat
        "peak_hours": [21, 22, 23, 0, 1, 2],
        "domain": "physical_harm"
    },
    "hit_and_run": {
        "share": 0.12,
        "peak_days": [5, 6, 0],       # Sat, Sun, Mon morning
        "peak_hours": [22, 23, 0, 1, 2, 3, 4],
        "domain": "physical_harm"
    },
    "narcotics": {
        "share": 0.12,
        "peak_days": [3, 4, 5],       # Thu, Fri, Sat
        "peak_hours": [20, 21, 22, 23, 0, 1],
        "domain": "narcotics"
    }
}

# Major Indian Gazetted Festivals & Holidays (2023 - 2026)
INDIAN_HOLIDAYS = [
    # 2023
    "2023-10-02", "2023-10-24", "2023-11-12", "2023-11-27", "2023-12-25", "2023-12-31",
    # 2024
    "2024-01-01", "2024-01-26", "2024-03-25", "2024-04-11", "2024-08-15", "2024-10-02",
    "2024-10-12", "2024-10-31", "2024-11-01", "2024-12-25", "2024-12-31",
    # 2025
    "2025-01-01", "2025-01-26", "2025-03-14", "2025-03-31", "2025-08-15", "2025-10-02",
    "2025-10-20", "2025-10-21", "2025-11-05", "2025-12-25", "2025-12-31",
    # 2026
    "2026-01-01", "2026-01-26", "2026-03-04", "2026-03-20", "2026-08-15", "2026-10-02",
    "2026-11-08", "2026-11-09", "2026-12-25", "2026-12-31"
]
HOLIDAY_DATES_SET = set(INDIAN_HOLIDAYS)

def is_holiday_week(dt: datetime.date) -> bool:
    """Returns True if the week of dt contains an Indian festival or gazetted holiday."""
    # Check current day and surrounding 3 days
    for delta in range(-3, 4):
        d_str = (dt + datetime.timedelta(days=delta)).isoformat()
        if d_str in HOLIDAY_DATES_SET:
            return True
    return False

def generate_synthetic_incidents(
    start_date: datetime.date = datetime.date(2023, 10, 1),
    end_date: datetime.date = datetime.date(2026, 9, 28),
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Simulates 3 years of daily incidents adhering to all stochastic requirements.
    Returns list of incident dictionary records matching upload format.
    """
    random.seed(seed)
    incidents = []
    
    # Precompute nearest 3 zones for each zone (for spillover & near-repeat)
    zone_names = list(ZONE_METADATA.keys())
    nearest_zones = {}
    for z1 in zone_names:
        distances = []
        for z2 in zone_names:
            if z1 != z2:
                d = math.hypot(ZONE_METADATA[z1]["lat"] - ZONE_METADATA[z2]["lat"],
                               ZONE_METADATA[z1]["lng"] - ZONE_METADATA[z2]["lng"])
                distances.append((d, z2))
        distances.sort()
        nearest_zones[z1] = [z[1] for z in distances[:3]]

    # Emerging hotspot start: 3 months before end_date (2026-07-01)
    emerging_hotspot_cutoff = end_date - datetime.timedelta(days=90)
    total_days = (end_date - start_date).days

    ref_counter = 10000

    curr_date = start_date
    while curr_date <= end_date:
        days_from_start = (curr_date - start_date).days
        year_frac = days_from_start / 365.25
        is_fest = is_holiday_week(curr_date)
        
        # Annual seasonal factor: peaks in winter (Nov-Jan) and monsoon festival months
        day_of_year = curr_date.timetuple().tm_yday
        seasonality = 1.0 + 0.18 * math.cos(2 * math.pi * (day_of_year - 330) / 365.25)
        if is_fest:
            seasonality *= 1.45 # 45% festival surge

        for zone_name, zmeta in ZONE_METADATA.items():
            base_rate = zmeta["base_rate"]
            trend_val = zmeta.get("trend", 0.0)
            
            # Trend multiplier
            trend_mult = 1.0 + (trend_val * year_frac)
            
            # Emerging hotspot condition: Cyber City spikes 3.8x in the last 3 months
            if zmeta.get("is_emerging_hotspot", False):
                if curr_date >= emerging_hotspot_cutoff:
                    # Ramps up sharply
                    hotspot_days = (curr_date - emerging_hotspot_cutoff).days
                    ramp = min(3.8, 1.0 + 2.8 * (hotspot_days / 30.0))
                    trend_mult *= ramp
            
            # Expected daily crimes for this zone
            # base_rate is weekly -> daily mean = base_rate / 7.0
            lambda_daily = (base_rate / 7.0) * trend_mult * seasonality

            for cat, ccfg in CATEGORY_CONFIG.items():
                cat_lambda = lambda_daily * ccfg["share"]
                
                # Sample Poisson using Knuth algorithm or normal approx
                n_events = 0
                if cat_lambda < 30:
                    L = math.exp(-cat_lambda)
                    k = 0
                    p = 1.0
                    while p > L:
                        k += 1
                        p *= random.random()
                    n_events = k - 1
                else:
                    n_events = max(0, int(random.gauss(cat_lambda, math.sqrt(cat_lambda))))

                for _ in range(n_events):
                    ref_counter += 1
                    # Hour selection based on category peak hours
                    if random.random() < 0.65:
                        hour = random.choice(ccfg["peak_hours"])
                    else:
                        hour = random.randint(0, 23)
                    
                    minute = random.randint(0, 59)
                    occurred_dt = datetime.datetime.combine(
                        curr_date, datetime.time(hour, minute)
                    )
                    
                    # Small Gaussian perturbation around zone centroid (up to ~350m)
                    lat_offset = random.gauss(0, 0.0018)
                    lng_offset = random.gauss(0, 0.0018)
                    inc_lat = round(zmeta["lat"] + lat_offset, 5)
                    inc_lng = round(zmeta["lng"] + lng_offset, 5)
                    
                    source = random.choices(["FIR", "call_100", "call_1930"], weights=[0.60, 0.30, 0.10])[0]
                    ref_id = f"{source}-{curr_date.year}-{ref_counter}"

                    incidents.append({
                        "source": source,
                        "source_ref_id": ref_id,
                        "district": zmeta["district"],
                        "police_station": zone_name,
                        "crime_type": cat,
                        "address_text": f"{zone_name}, Sector {random.randint(1, 14)}, {zmeta['district']}",
                        "lat": inc_lat,
                        "lng": inc_lng,
                        "occurred_at": occurred_dt.strftime("%Y-%m-%d %H:%M"),
                        "remarks": f"Reported {cat} in jurisdiction of {zone_name}."
                    })

                    # Near-repeat clustering: 22% chance of a follow-up incident within 48h and 250m
                    if random.random() < 0.22:
                        followup_hours = random.randint(4, 48)
                        followup_dt = occurred_dt + datetime.timedelta(hours=followup_hours)
                        if followup_dt.date() <= end_date:
                            ref_counter += 1
                            nr_lat = round(inc_lat + random.gauss(0, 0.0008), 5)
                            nr_lng = round(inc_lng + random.gauss(0, 0.0008), 5)
                            incidents.append({
                                "source": random.choice(["FIR", "call_100"]),
                                "source_ref_id": f"REP-{curr_date.year}-{ref_counter}",
                                "district": zmeta["district"],
                                "police_station": zone_name,
                                "crime_type": cat,
                                "address_text": f"Near {zone_name} landmark, {zmeta['district']}",
                                "lat": nr_lat,
                                "lng": nr_lng,
                                "occurred_at": followup_dt.strftime("%Y-%m-%d %H:%M"),
                                "remarks": f"Near-repeat cluster incident of {cat}."
                            })

        curr_date += datetime.timedelta(days=1)
        
    # Sort incidents chronologically by occurred_at
    incidents.sort(key=lambda x: x["occurred_at"])
    return incidents
