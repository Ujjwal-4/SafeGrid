"""
core/deduplicator.py
Spatio-temporal duplicate detection engine for police & emergency call logs.
Flags incidents with same location + category + date within a few hours as likely duplicates
(e.g., same incident reported via Dial-100 and subsequently filed as an FIR).
"""

import math
import datetime
from typing import List, Dict, Any, Tuple
from core.models import Incident

def haversine_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def normalize_address_for_comparison(addr: str) -> str:
    """Normalizes address string for token-based similarity."""
    cleaned = "".join([c.lower() if c.isalnum() or c.isspace() else " " for c in addr])
    tokens = set(cleaned.split())
    # Remove noise words
    noise = {"near", "opp", "opposite", "road", "marg", "street", "block", "sector", "lane", "area", "market"}
    tokens = tokens - noise
    return " ".join(sorted(tokens))

def parse_iso_datetime(dt_str: str) -> datetime.datetime:
    """Parses ISO timestamp string to datetime object."""
    clean = dt_str.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(clean)
    except Exception:
        return datetime.datetime.strptime(clean[:19], "%Y-%m-%d %H:%M:%S")

SOURCE_PRIORITY = {
    "fir": 10,
    "call_1930": 7,
    "call_100": 5,
    "manual_entry": 3
}

def detect_duplicates(
    incidents: List[Incident],
    max_distance_meters: float = 350.0,
    max_time_hours: float = 4.0
) -> Tuple[List[Incident], List[Dict[str, Any]]]:
    """
    Detects spatio-temporal duplicates among a list of Incident objects.
    
    Rules for matching:
    1. Same domain and category.
    2. Within max_distance_meters (haversine) OR strong address token overlap.
    3. Within max_time_hours between occurrence timestamps.
    
    Returns:
    - Processed list of incidents (with is_duplicate and duplicate_of metadata set)
    - List of duplicate linkage summaries
    """
    n = len(incidents)
    duplicate_pairs = []
    
    # Pre-parse timestamps
    timestamps = []
    for inc in incidents:
        try:
            timestamps.append(parse_iso_datetime(inc.occurred_at))
        except Exception:
            timestamps.append(datetime.datetime.min)
            
    # Track assigned duplicate relationships
    # Maps child_id -> parent_id
    duplicate_of_map = {}
    duplicate_reasons = {}
    
    for i in range(n):
        inc1 = incidents[i]
        t1 = timestamps[i]
        
        for j in range(i + 1, n):
            inc2 = incidents[j]
            t2 = timestamps[j]
            
            # Rule 1: Same category & domain
            if inc1.domain != inc2.domain or inc1.category != inc2.category:
                continue
                
            # Rule 2: Temporal proximity
            time_diff_sec = abs((t1 - t2).total_seconds())
            time_diff_hours = time_diff_sec / 3600.0
            if time_diff_hours > max_time_hours:
                continue
                
            # Rule 3: Spatial proximity
            dist_m = haversine_distance_meters(inc1.lat, inc1.lng, inc2.lat, inc2.lng)
            
            # Also check text similarity
            norm1 = normalize_address_for_comparison(inc1.address_text)
            norm2 = normalize_address_for_comparison(inc2.address_text)
            text_match = bool(norm1 and norm2 and (norm1 in norm2 or norm2 in norm1))
            
            is_spatial_match = (dist_m <= max_distance_meters) or text_match
            
            if is_spatial_match:
                # Decide which one is canonical
                prio1 = SOURCE_PRIORITY.get(str(inc1.source).lower(), 1)
                prio2 = SOURCE_PRIORITY.get(str(inc2.source).lower(), 1)
                
                # Higher source priority wins (e.g. FIR beats Dial-100 call).
                # If equal, the earlier incident is canonical.
                if prio1 > prio2:
                    canonical, duplicate = inc1, inc2
                elif prio2 > prio1:
                    canonical, duplicate = inc2, inc1
                elif t1 <= t2:
                    canonical, duplicate = inc1, inc2
                else:
                    canonical, duplicate = inc2, inc1
                    
                reason = (f"Spatiotemporal match: category '{inc1.category}', "
                          f"distance {dist_m:.0f}m, time delta {time_diff_hours:.1f}h "
                          f"({canonical.source.upper()} vs {duplicate.source.upper()})")
                          
                duplicate_pairs.append({
                    "canonical_id": canonical.id,
                    "duplicate_id": duplicate.id,
                    "canonical_source": canonical.source,
                    "duplicate_source": duplicate.source,
                    "distance_meters": round(dist_m, 1),
                    "time_diff_hours": round(time_diff_hours, 2),
                    "reason": reason
                })
                
                duplicate_of_map[duplicate.id] = canonical.id
                duplicate_reasons[duplicate.id] = reason

    # Update metadata in Incident objects
    for inc in incidents:
        if inc.id in duplicate_of_map:
            inc.metadata["is_duplicate"] = True
            inc.metadata["duplicate_of"] = duplicate_of_map[inc.id]
            inc.metadata["duplicate_reason"] = duplicate_reasons[inc.id]
        else:
            inc.metadata["is_duplicate"] = False
            inc.metadata["duplicate_of"] = None
            # Find any children linked to this canonical
            linked = [p["duplicate_id"] for p in duplicate_pairs if p["canonical_id"] == inc.id]
            if linked:
                inc.metadata["linked_duplicate_ids"] = linked

    return incidents, duplicate_pairs
