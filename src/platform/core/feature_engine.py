"""
core/feature_engine.py
Weekly Feature Engineering per (zone x category) matrix for SafeGrid Predictive Layer:
- Lags 1 through 8
- Rolling mean and rolling std for windows 4, 8, 12
- Week-of-year and Month (plus sine/cosine cyclical encoding)
- Indian holiday / festival flag
- Count of verified tips in that zone/category
- Recency-decayed count of recent nearby incidents (spatial-temporal decay)
- Mean lag of the 3 nearest zones (spatial spillover feature)
"""

import math
import datetime
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from core.synthetic_forecast_generator import ZONE_METADATA, is_holiday_week

def date_to_year_week(d: datetime.date) -> Tuple[int, int]:
    """Returns (iso_year, iso_week)."""
    return d.isocalendar()[:2]

def year_week_to_str(year: int, week: int) -> str:
    return f"{year}-W{week:02d}"

def str_to_year_week(yw_str: str) -> Tuple[int, int]:
    parts = yw_str.split("-W")
    return int(parts[0]), int(parts[1])

def get_week_start_date(year: int, week: int) -> datetime.date:
    """Returns the Monday of the given ISO year and week."""
    return datetime.date.fromisocalendar(year, week, 1)

def build_weekly_grid(
    incidents: List[Dict[str, Any]],
    tips: Optional[List[Dict[str, Any]]] = None,
    all_categories: Optional[List[str]] = None
) -> Tuple[Dict[Tuple[str, str], Dict[str, float]], List[str], Dict[str, List[str]]]:
    """
    Aggregates incidents into a weekly count series per (zone, category).
    Returns:
    - series: (zone, category) -> { "YYYY-Www": count }
    - ordered_weeks: sorted list of "YYYY-Www" strings covering all dates
    - nearest_3_map: zone -> list of 3 nearest zone names
    """
    if all_categories is None:
        all_categories = ["theft", "burglary", "assault", "hit_and_run", "narcotics"]
        
    zone_names = list(ZONE_METADATA.keys())

    # Precalculate nearest 3 zones for each zone
    nearest_3_map = {}
    for z1 in zone_names:
        dists = []
        for z2 in zone_names:
            if z1 != z2:
                d = math.hypot(ZONE_METADATA[z1]["lat"] - ZONE_METADATA[z2]["lat"],
                               ZONE_METADATA[z1]["lng"] - ZONE_METADATA[z2]["lng"])
                dists.append((d, z2))
        dists.sort()
        nearest_3_map[z1] = [x[1] for x in dists[:3]]

    # Parse dates and count
    raw_counts = defaultdict(lambda: defaultdict(int)) # (zone, cat) -> week_str -> count
    all_weeks_set = set()

    for inc in incidents:
        if isinstance(inc, dict):
            dt_str = inc.get("occurred_at", "")
            zone = inc.get("police_station") or inc.get("zone")
            cat = inc.get("crime_type") or inc.get("category")
        else:
            dt_str = getattr(inc, "occurred_at", "")
            zone = getattr(inc, "police_station", None) or getattr(inc, "district", None)
            cat = getattr(inc, "category", "") or getattr(inc, "domain", "")

        if not dt_str:
            continue
        try:
            dt = datetime.datetime.strptime(dt_str[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        
        y, w = date_to_year_week(dt)
        w_str = year_week_to_str(y, w)
        all_weeks_set.add((y, w))
        
        if zone and cat:
            raw_counts[(zone, cat.lower())][w_str] += 1

    if not all_weeks_set:
        # Fallback to current year
        now = datetime.date.today()
        all_weeks_set.add(date_to_year_week(now))

    sorted_tuples = sorted(list(all_weeks_set))
    start_y, start_w = sorted_tuples[0]
    end_y, end_w = sorted_tuples[-1]

    # Generate contiguous sequence of weeks
    ordered_weeks = []
    curr = get_week_start_date(start_y, start_w)
    end_date = get_week_start_date(end_y, end_w)
    while curr <= end_date:
        y, w = date_to_year_week(curr)
        ordered_weeks.append(year_week_to_str(y, w))
        curr += datetime.timedelta(days=7)

    # Normalize series to contain 0.0 for every week
    weekly_series = {}
    for zone in zone_names:
        for cat in all_categories:
            key = (zone, cat)
            s_map = {}
            for w_str in ordered_weeks:
                s_map[w_str] = float(raw_counts[key].get(w_str, 0))
            weekly_series[key] = s_map

    return weekly_series, ordered_weeks, nearest_3_map

def compute_rolling_stats(vals: List[float], window: int) -> Tuple[float, float]:
    """Computes mean and sample std over vals[-window:]."""
    if len(vals) < window:
        subset = vals
    else:
        subset = vals[-window:]
    if not subset:
        return 0.0, 0.0
    mean_val = sum(subset) / len(subset)
    if len(subset) > 1:
        variance = sum((x - mean_val) ** 2 for x in subset) / (len(subset) - 1)
        std_val = math.sqrt(variance)
    else:
        std_val = 0.0
    return mean_val, std_val

def extract_features_for_series(
    zone: str,
    category: str,
    weekly_series: Dict[Tuple[str, str], Dict[str, float]],
    ordered_weeks: List[str],
    nearest_3_map: Dict[str, List[str]],
    verified_tips_by_zone_cat_week: Optional[Dict[Tuple[str, str, str], int]] = None
) -> List[Dict[str, Any]]:
    """
    Extracts feature rows for every week t >= 12 (requiring 12 weeks of lag history).
    Each feature dict contains:
    - target: y_t (actual count)
    - lags: lag_1 through lag_8
    - rolling stats: mean/std for 4, 8, 12
    - calendar features: week_of_year, month, sin/cos cyclical
    - holiday_flag
    - verified_tips_count
    - recency_decayed_incidents
    - mean_lag_3_nearest (spatial lag)
    """
    if verified_tips_by_zone_cat_week is None:
        verified_tips_by_zone_cat_week = {}

    own_counts = [weekly_series[(zone, category)][w] for w in ordered_weeks]
    n_weeks = len(ordered_weeks)
    features = []

    for t in range(12, n_weeks):
        w_str = ordered_weeks[t]
        y_val = own_counts[t]
        past = own_counts[:t] # past values up to t-1

        # Lags 1-8
        lag_1 = past[-1] if len(past) >= 1 else 0.0
        lag_2 = past[-2] if len(past) >= 2 else 0.0
        lag_3 = past[-3] if len(past) >= 3 else 0.0
        lag_4 = past[-4] if len(past) >= 4 else 0.0
        lag_5 = past[-5] if len(past) >= 5 else 0.0
        lag_6 = past[-6] if len(past) >= 6 else 0.0
        lag_7 = past[-7] if len(past) >= 7 else 0.0
        lag_8 = past[-8] if len(past) >= 8 else 0.0

        # Rolling stats
        mean_4, std_4 = compute_rolling_stats(past, 4)
        mean_8, std_8 = compute_rolling_stats(past, 8)
        mean_12, std_12 = compute_rolling_stats(past, 12)

        # Date & cyclical
        year, week_num = str_to_year_week(w_str)
        monday_dt = get_week_start_date(year, week_num)
        month_num = monday_dt.month
        
        sin_week = math.sin(2 * math.pi * week_num / 52.0)
        cos_week = math.cos(2 * math.pi * week_num / 52.0)
        sin_month = math.sin(2 * math.pi * month_num / 12.0)
        cos_month = math.cos(2 * math.pi * month_num / 12.0)

        # Holiday flag
        holiday_flag = 1.0 if is_holiday_week(monday_dt) else 0.0

        # Verified tips
        tips_count = float(verified_tips_by_zone_cat_week.get((zone, category, w_str), 0))

        # Recency-decayed recent nearby incident count (exponential time decay across past 4 weeks)
        decayed_sum = (
            lag_1 * math.exp(-0.15 * 1) +
            lag_2 * math.exp(-0.15 * 2) +
            lag_3 * math.exp(-0.15 * 3) +
            lag_4 * math.exp(-0.15 * 4)
        )

        # Mean lag of 3 nearest zones
        near_zones = nearest_3_map.get(zone, [])
        near_lags = []
        for nz in near_zones:
            nz_past = [weekly_series.get((nz, category), {}).get(w, 0.0) for w in ordered_weeks[:t]]
            near_lags.append(nz_past[-1] if nz_past else 0.0)
        mean_lag_3_nearest = sum(near_lags) / max(1, len(near_lags))

        features.append({
            "period": w_str,
            "zone": zone,
            "category": category,
            "target": y_val,
            "lag_1": lag_1,
            "lag_2": lag_2,
            "lag_3": lag_3,
            "lag_4": lag_4,
            "lag_5": lag_5,
            "lag_6": lag_6,
            "lag_7": lag_7,
            "lag_8": lag_8,
            "rolling_mean_4": mean_4,
            "rolling_std_4": std_4,
            "rolling_mean_8": mean_8,
            "rolling_std_8": std_8,
            "rolling_mean_12": mean_12,
            "rolling_std_12": std_12,
            "week_of_year": float(week_num),
            "month": float(month_num),
            "sin_week": sin_week,
            "cos_week": cos_week,
            "sin_month": sin_month,
            "cos_month": cos_month,
            "holiday_flag": holiday_flag,
            "verified_tips_count": tips_count,
            "recency_decayed_incidents": decayed_sum,
            "mean_lag_3_nearest": mean_lag_3_nearest
        })

    return features
