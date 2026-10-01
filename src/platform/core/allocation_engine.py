"""
core/allocation_engine.py
Prescriptive Patrol Resource Allocation Engine for SafeGrid.
Distributes N patrol units across zones in proportion to forecast crime frequency:
- Guaranteed minimum unit (1 car) for zones exceeding threshold
- Maximum allocation cap per zone to prevent over-concentration
- Exact Hamilton-Hare Largest Remainder integer apportionment
- Outputs pure numeric rationale (LLM narration occurs at the reporting layer)
"""

import math
from typing import List, Dict, Any, Optional

def compute_patrol_allocation(
    zone_forecasts: List[Dict[str, Any]],
    total_units: int = 20,
    min_threshold: float = 3.0,
    max_cap_share: float = 0.35
) -> List[Dict[str, Any]]:
    """
    Distributes total_units patrol cars among zones based on forecast frequency.
    zone_forecasts: list of dicts with keys 'zone' and 'forecast'.
    Returns list of allocation dicts:
    [
      {
        "zone": str,
        "recommended_units": int,
        "share": float,
        "forecast": float,
        "rationale": {
          "forecast_share": float,
          "base_allocation": float,
          "adjusted_units": int,
          "min_enforced": bool,
          "cap_enforced": bool
        }
      }
    ]
    """
    if not zone_forecasts or total_units <= 0:
        return []

    n_zones = len(zone_forecasts)
    total_forecast = sum(max(0.0, float(zf.get("forecast", 0.0))) for zf in zone_forecasts)
    if total_forecast <= 0:
        # Uniform fallback
        base_each = total_units // n_zones
        rem = total_units % n_zones
        res = []
        for i, zf in enumerate(zone_forecasts):
            units = base_each + (1 if i < rem else 0)
            res.append({
                "zone": zf.get("zone", "Unknown"),
                "recommended_units": units,
                "share": round(units / total_units, 4),
                "forecast": 0.0,
                "rationale": {
                    "forecast_share": round(1.0 / n_zones, 4),
                    "base_allocation": round(total_units / n_zones, 2),
                    "adjusted_units": units,
                    "min_enforced": False,
                    "cap_enforced": False
                }
            })
        return res

    # 1. Base proportional share
    max_cap_units = max(2.0, total_units * max_cap_share)
    raw_allocations = []
    
    for zf in zone_forecasts:
        f_val = max(0.0, float(zf.get("forecast", 0.0)))
        f_share = f_val / total_forecast
        raw_units = total_units * f_share
        
        min_flag = False
        cap_flag = False

        if f_val >= min_threshold and raw_units < 1.0:
            raw_units = 1.0
            min_flag = True

        if raw_units > max_cap_units:
            raw_units = max_cap_units
            cap_flag = True

        raw_allocations.append({
            "zone": zf.get("zone", "Unknown"),
            "district": zf.get("district", ""),
            "state": zf.get("state", ""),
            "forecast": round(f_val, 2),
            "forecast_share": round(f_share, 4),
            "base_raw": raw_units,
            "min_enforced": min_flag,
            "cap_enforced": cap_flag
        })

    # 2. Rescale raw units to sum exactly to total_units
    sum_raw = sum(x["base_raw"] for x in raw_allocations)
    scaling = total_units / sum_raw if sum_raw > 0 else 1.0
    
    scaled = []
    for x in raw_allocations:
        adj = x["base_raw"] * scaling
        scaled.append({**x, "adj_float": adj})

    # 3. Integer apportionment using Hamilton-Hare Largest Remainder Method
    integer_parts = [math.floor(x["adj_float"]) for x in scaled]
    remainders = [(scaled[i]["adj_float"] - integer_parts[i], i) for i in range(len(scaled))]
    remainders.sort(reverse=True, key=lambda r: r[0])

    allocated_units = integer_parts[:]
    unallocated = total_units - sum(integer_parts)

    for step in range(unallocated):
        idx = remainders[step % len(remainders)][1]
        allocated_units[idx] += 1

    # Formulate output
    output = []
    for i, item in enumerate(scaled):
        final_units = allocated_units[i]
        output.append({
            "zone": item["zone"],
            "district": item["district"],
            "state": item["state"],
            "recommended_units": final_units,
            "share": round(final_units / total_units, 4),
            "forecast": item["forecast"],
            "rationale": {
                "forecast_share": item["forecast_share"],
                "base_allocation": round(item["adj_float"], 2),
                "adjusted_units": final_units,
                "min_enforced": item["min_enforced"],
                "cap_enforced": item["cap_enforced"]
            }
        })

    # Sort descending by recommended units
    output.sort(key=lambda x: x["recommended_units"], reverse=True)
    return output
