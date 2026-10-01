"""
core/geocoder.py
Geocoding module using OpenStreetMap Nominatim with:
- Strict ~1 req/sec rate limit queue/delay enforcement.
- Custom User-Agent header (required by Nominatim terms of service).
- Persistent SQLite cache to eliminate redundant API calls.
- High-precision local gazetteer fallback for district landmarks & offline resilience.
"""

import os
import time
import json
import sqlite3
import hashlib
import urllib.parse
import urllib.request
import threading
from typing import Dict, Any, Optional, Tuple

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_USER_AGENT = "CrimeNarcoticsIntelPlatform/1.0 (internal-police-intel@gov.in)"

# Pre-seeded gazetteer for metropolitan districts & landmarks
SEEDED_GAZETTEER = {
    # District centers
    "new delhi": (28.6315, 77.2167),
    "central": (28.6450, 77.2120),
    "north": (28.6700, 77.2180),
    "north west": (28.6980, 77.1650),
    "west": (28.6500, 77.1200),
    "south west": (28.5700, 77.0800),
    "south": (28.5300, 77.2100),
    "south east": (28.5600, 77.2600),
    "east": (28.6300, 77.2900),
    "shahdara": (28.6700, 77.2900),
    "north east": (28.7000, 77.2700),
    "rohini": (28.7300, 77.1100),
    "outer": (28.7000, 77.0500),
    "outer north": (28.8100, 77.1100),
    "dwarka": (28.5800, 77.0500),
    "gurugram east": (28.4700, 77.0700),
    "noida central": (28.5700, 77.3400),
    "faridabad nit": (28.4000, 77.3000),
    
    # Specific landmarks and colonies
    "connaught place": (28.6315, 77.2167),
    "shivaji stadium": (28.6290, 77.2135),
    "chanakyapuri": (28.5950, 77.1850),
    "janpath": (28.6250, 77.2180),
    "tolstoy marg": (28.6270, 77.2210),
    "mandir marg": (28.6320, 77.1990),
    "paharganj": (28.6430, 77.2140),
    "karol bagh": (28.6520, 77.1900),
    "daryaganj": (28.6460, 77.2400),
    "turkman gate": (28.6440, 77.2340),
    "gb road": (28.6470, 77.2230),
    "chandni chowk": (28.6560, 77.2300),
    "kashmere gate": (28.6670, 77.2280),
    "civil lines": (28.6810, 77.2240),
    "mukherjee nagar": (28.7060, 77.2140),
    "model town": (28.7020, 77.1930),
    "ashok vihar": (28.6940, 77.1740),
    "azadpur": (28.7090, 77.1780),
    "rajouri garden": (28.6490, 77.1220),
    "punjabi bagh": (28.6680, 77.1320),
    "tilak nagar": (28.6360, 77.0960),
    "janakpuri": (28.6220, 77.0850),
    "vasant kunj": (28.5290, 77.1520),
    "delhi cantt": (28.5980, 77.1260),
    "palam": (28.5830, 77.0850),
    "hauz khas": (28.5490, 77.2000),
    "saket": (28.5240, 77.2060),
    "malviya nagar": (28.5320, 77.2100),
    "lajpat nagar": (28.5700, 77.2430),
    "kalkaji": (28.5400, 77.2580),
    "nehru place": (28.5480, 77.2510),
    "preet vihar": (28.6410, 77.2960),
    "mayur vihar": (28.6080, 77.2950),
    "laxmi nagar": (28.6310, 77.2770),
    "anand vihar": (28.6470, 77.3150),
    "seelampur": (28.6690, 77.2660),
    "jafrabad": (28.6850, 77.2730),
    "narela": (28.8520, 77.0930),
    "bawana": (28.7980, 77.0350),
    "cyber city": (28.4950, 77.0890),
    "atta market": (28.5700, 77.3220)
}

class NominatimGeocoder:
    def __init__(self, db_path: str = "geocache.sqlite", min_request_interval: float = 1.1):
        if db_path == "geocache.sqlite" and not os.path.exists(db_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            cand1 = os.path.join(base_dir, "data", "geocache.sqlite")
            cand2 = os.path.join(base_dir, "geocache.sqlite")
            if os.path.exists(cand1):
                db_path = cand1
            elif os.path.exists(cand2):
                db_path = cand2
        self.db_path = db_path
        self.min_request_interval = min_request_interval
        self.last_request_time = 0.0
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    address_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    display_name TEXT,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _get_cache(self, query: str) -> Optional[Dict[str, Any]]:
        norm = query.strip().lower()
        h = hashlib.sha256(norm.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lat, lng, display_name, source FROM geocode_cache WHERE address_hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                return {
                    "lat": row[0],
                    "lng": row[1],
                    "display_name": row[2],
                    "source": row[3]
                }
        return None

    def _save_cache(self, query: str, lat: float, lng: float, display_name: str, source: str):
        norm = query.strip().lower()
        h = hashlib.sha256(norm.encode('utf-8')).hexdigest()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO geocode_cache (address_hash, query, lat, lng, display_name, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (h, norm, lat, lng, display_name, source))
                conn.commit()
        except Exception:
            pass

    def _lookup_gazetteer(self, query: str, district: Optional[str] = None) -> Optional[Tuple[float, float, str]]:
        """Matches landmarks in query or district against local gazetteer."""
        norm = query.lower()
        for key, coords in SEEDED_GAZETTEER.items():
            if key in norm:
                # Add deterministic small offset based on address text hash (~50-150m) so multiple addresses don't stack on 1 point
                h_val = int(hashlib.md5(norm.encode('utf-8')).hexdigest()[:6], 16)
                offset_lat = ((h_val % 100) - 50) * 0.00008
                offset_lng = (((h_val // 100) % 100) - 50) * 0.00008
                return (round(coords[0] + offset_lat, 6), round(coords[1] + offset_lng, 6), f"Gazetteer match: {key}")
                
        if district:
            dist_norm = district.strip().lower()
            for key, coords in SEEDED_GAZETTEER.items():
                if key in dist_norm or dist_norm in key:
                    h_val = int(hashlib.md5(norm.encode('utf-8')).hexdigest()[:6], 16)
                    offset_lat = ((h_val % 100) - 50) * 0.00015
                    offset_lng = (((h_val // 100) % 100) - 50) * 0.00015
                    return (round(coords[0] + offset_lat, 6), round(coords[1] + offset_lng, 6), f"District centroid: {key}")
                    
        return None

    def geocode(self, address_text: str, district: Optional[str] = None, allow_network: bool = True) -> Dict[str, Any]:
        """
        Geocodes address_text into {lat, lng, display_name, source}.
        1. Checks SQLite cache.
        2. If allow_network=True and not in cache, throttles to 1 req/sec and queries Nominatim.
        3. Falls back to high-accuracy gazetteer if network blocked, offline, or not found.
        """
        if not address_text:
            return {"lat": 28.6139, "lng": 77.2090, "display_name": "Default City Center", "source": "fallback"}
            
        full_query = address_text
        if district and district.lower() not in address_text.lower():
            full_query = f"{address_text}, {district}"
            
        # 1. Cache hit
        cached = self._get_cache(full_query)
        if cached:
            return cached
            
        # 2. Check gazetteer before external network to be ultra-fast and resilient
        gazetteer_match = self._lookup_gazetteer(address_text, district)
        
        # 3. Nominatim HTTP query with 1 request/second rate limiting
        if allow_network:
            with self.lock:
                now = time.monotonic()
                time_since_last = now - self.last_request_time
                if time_since_last < self.min_request_interval:
                    sleep_time = self.min_request_interval - time_since_last
                    time.sleep(sleep_time)
                self.last_request_time = time.monotonic()
                
            try:
                params = {
                    "q": full_query,
                    "format": "json",
                    "limit": "1",
                    "addressdetails": "1"
                }
                url = f"{NOMINATIM_SEARCH_URL}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if data and len(data) > 0:
                            lat = float(data[0]["lat"])
                            lng = float(data[0]["lon"])
                            display_name = data[0].get("display_name", address_text)
                            self._save_cache(full_query, lat, lng, display_name, "nominatim")
                            return {
                                "lat": lat,
                                "lng": lng,
                                "display_name": display_name,
                                "source": "nominatim"
                            }
            except Exception:
                # Network failed or timed out or offline
                pass
                
        # 4. Fallback to gazetteer match if Nominatim fails or network disabled
        if gazetteer_match:
            lat, lng, label = gazetteer_match
            self._save_cache(full_query, lat, lng, label, "gazetteer")
            return {
                "lat": lat,
                "lng": lng,
                "display_name": f"{address_text} ({label})",
                "source": "gazetteer"
            }
            
        # 5. Default metropolitan baseline
        default_lat, default_lng = 28.6139, 77.2090
        return {
            "lat": default_lat,
            "lng": default_lng,
            "display_name": f"{address_text} (Approximate)",
            "source": "approximate_baseline"
        }
