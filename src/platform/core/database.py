"""
core/database.py
SQLite storage layer for incidents, tips, officers/users, and domain intelligence.
"""

import os
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from core.models import Incident, Tip, User

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "platform.sqlite")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_schema()
        self.seed_users()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Incidents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_ref_id TEXT,
                    district TEXT NOT NULL,
                    police_station TEXT,
                    lat REAL NOT NULL,
                    lng REAL NOT NULL,
                    address_text TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    indicators_json TEXT,
                    metadata_json TEXT
                )
            """)
            
            # Tips table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tips (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    category TEXT NOT NULL,
                    district TEXT NOT NULL,
                    description TEXT NOT NULL,
                    photo_url TEXT,
                    lat REAL,
                    lng REAL,
                    status TEXT NOT NULL,
                    is_high_priority INTEGER NOT NULL,
                    is_urgent INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    verified_by TEXT,
                    verified_at TEXT
                )
            """)
            
            # Users / Officers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    badge_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    district TEXT,
                    password_hash TEXT NOT NULL
                )
            """)

            # Model Metrics history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trained_at TEXT NOT NULL,
                    n_incidents INTEGER NOT NULL,
                    mae REAL NOT NULL,
                    poisson_deviance REAL NOT NULL,
                    hit_rate_top5 REAL NOT NULL,
                    pai REAL NOT NULL,
                    champion_model TEXT NOT NULL
                )
            """)

            # Audit Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_badge TEXT,
                    details_json TEXT
                )
            """)
            
            conn.commit()

    def seed_users(self):
        """Seeds default law enforcement officers, admin, and supervisor."""
        users_to_seed = [
            ("usr-adm-01", "admin", "System Administrator", "supervisor", None, hash_password("admin")),
            ("usr-adm-02", "ADMIN-001", "Chief Admin Officer", "supervisor", None, hash_password("admin_pass")),
            ("usr-sup-01", "SUPER-101", "Supervisor Rao", "supervisor", None, hash_password("supervisor_pass")),
            ("usr-off-01", "OFFICER-001", "Inspector Sharma", "officer", "New Delhi", hash_password("officer_pass")),
            ("usr-off-02", "OFFICER-002", "Sub-Inspector Verma", "officer", "Central", hash_password("officer_pass"))
        ]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for uid, badge, name, role, dist, pwd_h in users_to_seed:
                cursor.execute("""
                    INSERT OR REPLACE INTO users (id, badge_id, name, role, district, password_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (uid, badge, name, role, dist, pwd_h))
            conn.commit()

    def get_user_by_badge(self, badge_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, badge_id, name, role, district, password_hash FROM users WHERE UPPER(badge_id) = UPPER(?)", (badge_id.strip(),))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def insert_incidents(self, incidents: List[Incident]) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for inc in incidents:
                cursor.execute("""
                    INSERT OR REPLACE INTO incidents (
                        id, domain, category, source, source_ref_id, district, police_station,
                        lat, lng, address_text, occurred_at, created_at, indicators_json, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inc.id, inc.domain, inc.category, inc.source, inc.source_ref_id,
                    inc.district, inc.police_station, inc.lat, inc.lng, inc.address_text,
                    inc.occurred_at, inc.created_at,
                    json.dumps(inc.indicators), json.dumps(inc.metadata)
                ))
                count += 1
            conn.commit()
            return count

    def get_incidents(
        self,
        domain: Optional[str] = None,
        district: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 1000
    ) -> List[Incident]:
        query = "SELECT * FROM incidents WHERE 1=1"
        params = []
        if domain:
            query += " AND domain = ?"
            params.append(domain.lower())
        if district:
            query += " AND district = ?"
            params.append(district)
        if category:
            query += " AND category = ?"
            params.append(category.lower())
            
        query += " ORDER BY occurred_at DESC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
        results = []
        for r in rows:
            indicators = json.loads(r["indicators_json"]) if r["indicators_json"] else {}
            metadata = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            results.append(Incident(
                id=r["id"],
                domain=r["domain"],
                category=r["category"],
                source=r["source"],
                source_ref_id=r["source_ref_id"],
                district=r["district"],
                police_station=r["police_station"],
                lat=r["lat"],
                lng=r["lng"],
                address_text=r["address_text"],
                occurred_at=r["occurred_at"],
                created_at=r["created_at"],
                indicators=indicators,
                metadata=metadata
            ))
        return results

    def insert_tip(self, tip: Tip) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tips (
                    id, domain, category, district, description, photo_url,
                    lat, lng, status, is_high_priority, is_urgent, created_at, verified_by, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tip.id, tip.domain, tip.category, tip.district, tip.description, tip.photo_url,
                tip.lat, tip.lng, tip.status, 1 if tip.is_high_priority else 0,
                1 if tip.is_urgent else 0, tip.created_at, tip.verified_by, tip.verified_at
            ))
            conn.commit()
            return tip.id

    def get_tips(
        self,
        status: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tips WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
            
        target_dist = district or region
        if target_dist:
            query += " AND district = ?"
            params.append(target_dist)
            
        query += " ORDER BY created_at DESC"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
        tips = []
        for r in rows:
            dist = r["district"]
            tips.append({
                "id": r["id"],
                "region": dist,
                "district": dist,
                "domain": r["domain"],
                "category": r["category"],
                "description": r["description"],
                "photo_url": r["photo_url"],
                "lat": r["lat"],
                "lng": r["lng"],
                "status": r["status"],
                "is_high_priority": bool(r["is_high_priority"]),
                "is_urgent": bool(r["is_urgent"]),
                "created_at": r["created_at"],
                "verified_by": r["verified_by"],
                "verified_at": r["verified_at"]
            })
        return tips

    def update_tip_status(self, tip_id: str, status: str, verified_by: str, verified_at: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tips
                SET status = ?, verified_by = ?, verified_at = ?
                WHERE id = ?
            """, (status, verified_by, verified_at, tip_id))
            conn.commit()
            
            cursor.execute("SELECT * FROM tips WHERE id = ?", (tip_id,))
            r = cursor.fetchone()
            if r:
                dist = r["district"]
                return {
                    "id": r["id"],
                    "region": dist,
                    "district": dist,
                    "domain": r["domain"],
                    "category": r["category"],
                    "description": r["description"],
                    "photo_url": r["photo_url"],
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "status": r["status"],
                    "is_high_priority": bool(r["is_high_priority"]),
                    "is_urgent": bool(r["is_urgent"]),
                    "created_at": r["created_at"],
                    "verified_by": r["verified_by"],
                    "verified_at": r["verified_at"]
                }
        return None

    def insert_model_metric(
        self,
        trained_at: str,
        n_incidents: int,
        mae: float,
        poisson_deviance: float,
        hit_rate_top5: float,
        pai: float,
        champion_model: str
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO model_metrics (
                    trained_at, n_incidents, mae, poisson_deviance, hit_rate_top5, pai, champion_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (trained_at, n_incidents, mae, poisson_deviance, hit_rate_top5, pai, champion_model))
            conn.commit()
            return cursor.lastrowid

    def get_model_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT trained_at, n_incidents, mae, poisson_deviance, hit_rate_top5, pai, champion_model
                FROM model_metrics
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def log_audit(self, action: str, user_badge: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        import datetime
        with self.get_connection() as conn:
            cursor = conn.cursor()
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO audit_logs (action, timestamp, user_badge, details_json)
                VALUES (?, ?, ?, ?)
            """, (action, ts, user_badge, json.dumps(details or {})))
            conn.commit()

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT action, timestamp, user_badge, details_json
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            res = []
            for r in rows:
                item = dict(r)
                if item.get("details_json"):
                    try:
                        item["details"] = json.loads(item["details_json"])
                    except Exception:
                        item["details"] = {}
                res.append(item)
            return res
