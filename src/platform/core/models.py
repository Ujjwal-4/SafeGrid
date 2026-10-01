"""
core/models.py
Data models and schemas for the crime/narcotics intelligence ingestion platform.
Strictly adheres to specified schemas:
1. Incident
2. Tip
3. DomainConfig
4. Hotspot API response
5. Officer / auth
"""

import uuid
import datetime
from typing import Dict, Any, List, Optional

class Incident:
    """
    Schema 1: Incident (from FIR / 100 / 1930 uploads)
    {
      "id": "string (UUID)",
      "domain": "narcotics | crime",
      "category": "string",
      "source": "fir | call_100 | call_1930 | manual_entry",
      "source_ref_id": "string | null",
      "district": "string",
      "police_station": "string | null",
      "lat": "number",
      "lng": "number",
      "address_text": "string",
      "occurred_at": "ISO 8601 timestamp",
      "created_at": "ISO 8601 timestamp",
      "metadata": "object | null"
    }
    Requirement 6: { id, domain, category, lat, lng, address_text, date, source, indicators }
    """
    def __init__(
        self,
        domain: str,
        category: str,
        source: str,
        lat: float,
        lng: float,
        address_text: str,
        occurred_at: str,
        id: Optional[str] = None,
        source_ref_id: Optional[str] = None,
        district: Optional[str] = "Unknown",
        police_station: Optional[str] = None,
        created_at: Optional[str] = None,
        indicators: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.domain = domain.lower()
        self.category = category.lower()
        
        # Normalize source to "FIR" | "call_100" | "call_1930"
        src_raw = str(source).strip()
        if src_raw.lower() == "fir":
            self.source = "FIR"
        elif "100" in src_raw.lower():
            self.source = "call_100"
        elif "1930" in src_raw.lower():
            self.source = "call_1930"
        else:
            self.source = src_raw

        self.source_ref_id = source_ref_id
        self.district = district or "Unknown"
        self.police_station = police_station
        self.lat = float(lat)
        self.lng = float(lng)
        self.address_text = address_text
        self.occurred_at = occurred_at
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.indicators = indicators or {}
        self.metadata = metadata or {}
        
        # Ensure indicators is accessible in metadata as well
        if indicators and "indicators" not in self.metadata:
            self.metadata["indicators"] = indicators

    def to_dict(self) -> Dict[str, Any]:
        """Returns dict matching integration prompt and Schemas 1 & 6."""
        return {
            "id": self.id,
            "domain": self.domain,
            "category": self.category,
            "lat": self.lat,
            "lng": self.lng,
            "address_text": self.address_text,
            "date": self.occurred_at,          # Required in integration schema
            "source": self.source,             # "FIR" | "call_100" | "call_1930"
            "indicators": self.indicators,      # Required in integration schema
            "source_ref_id": self.source_ref_id,
            "district": self.district,
            "police_station": self.police_station,
            "occurred_at": self.occurred_at,
            "created_at": self.created_at,
            "metadata": self.metadata
        }

class Tip:
    """
    Schema 2 & Integration Tip:
    { id, region, category, description, photo_url?, lat?, lng?,
      created_at, status: "pending"|"verified_true"|"verified_false",
      verified_by?, verified_at? }
    """
    def __init__(
        self,
        category: str,
        description: str,
        region: Optional[str] = None,
        district: Optional[str] = None,
        domain: Optional[str] = "narcotics",
        id: Optional[str] = None,
        photo_url: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        status: str = "pending",
        is_high_priority: bool = False,
        is_urgent: bool = False,
        created_at: Optional[str] = None,
        verified_by: Optional[str] = None,
        verified_at: Optional[str] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.domain = (domain or "narcotics").lower()
        self.category = category.lower()
        self.region = region or district or "Unknown"
        self.district = self.region
        self.description = description
        self.photo_url = photo_url
        self.lat = float(lat) if lat is not None else None
        self.lng = float(lng) if lng is not None else None
        self.status = status
        self.is_high_priority = bool(is_high_priority)
        self.is_urgent = bool(is_urgent)
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.verified_by = verified_by
        self.verified_at = verified_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "region": self.region,             # Integration schema requirement
            "district": self.district,         # Schema 2 requirement
            "domain": self.domain,
            "category": self.category,
            "description": self.description,
            "photo_url": self.photo_url,
            "lat": self.lat,
            "lng": self.lng,
            "created_at": self.created_at,
            "status": self.status,
            "is_high_priority": self.is_high_priority,
            "is_urgent": self.is_urgent,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at
        }

class HotspotEntry:
    """
    Integration & Schema 4 Hotspot API response:
    [{ zone, lat, lng, score, category }] + { district, domain, frequency, previous_frequency, trend }
    """
    def __init__(
        self,
        district: str,
        domain: str,
        category: str,
        lat: float,
        lng: float,
        frequency: int,
        previous_frequency: int,
        trend: str,
        zone: Optional[str] = None,
        score: Optional[float] = None,
        color: Optional[str] = None
    ):
        self.district = district or zone or "Unknown"
        self.zone = self.district
        self.domain = domain
        self.category = category
        self.lat = float(lat)
        self.lng = float(lng)
        self.frequency = int(frequency)
        self.score = score if score is not None else int(frequency)
        self.previous_frequency = int(previous_frequency)
        self.trend = trend.lower()
        self.color = color

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "zone": self.zone,                  # Integration schema requirement
            "district": self.district,          # Schema 4 requirement
            "category": self.category,
            "lat": self.lat,
            "lng": self.lng,
            "score": self.score,                # Integration schema requirement (raw frequency or score)
            "frequency": self.frequency,        # Schema 4 requirement
            "previous_frequency": self.previous_frequency,
            "trend": self.trend,
            "domain": self.domain
        }
        if self.color:
            d["color"] = self.color
        return d

class User:
    """
    Schema 5: Officer / auth
    User: { "id": "string", "badge_id": "string", "name": "string", "role": "officer | supervisor", "district": "string | null" }
    """
    def __init__(
        self,
        badge_id: str,
        name: str,
        role: str,
        id: Optional[str] = None,
        district: Optional[str] = None,
        password_hash: Optional[str] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.badge_id = badge_id
        self.name = name
        self.role = role.lower()  # "officer" | "supervisor"
        self.district = district
        self.password_hash = password_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "name": self.name,
            "role": self.role,
            "district": self.district
        }
