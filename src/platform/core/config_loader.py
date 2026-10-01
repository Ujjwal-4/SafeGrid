"""
core/config_loader.py
Loads, validates, and manages domain configurations (YAML and JSON).
Handles category synonym normalization and indicator weights.
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional

CATEGORY_ALIASES = {
    "physical_harm": {
        "murder": [
            "murder", "attempt to murder", "attempted murder", "killing", "homicide",
            "lethal assault", "fatal attack", "murder / attempt to murder", "shooting"
        ],
        "assault": [
            "assault", "hurt", "assault / hurt", "fights", "street brawls",
            "physical fight", "battery", "beating", "grievous hurt", "quarrel",
            "scuffle", "weapon attack", "brawl", "simple hurt"
        ],
        "hit_and_run": [
            "hit_and_run", "hit and run", "hit & run", "hit-and-run",
            "negligent driving", "accident hit and run", "vehicle collision fleeing",
            "fled scene accident", "rash driving death", "road accident hit and run",
            "fatal accident", "road accident", "rash driving"
        ],
        "kidnapping": [
            "kidnapping", "abduction", "kidnap", "child kidnapping", "abduction by force",
            "baiting", "hostage", "illegal confinement"
        ]
    },
    "women_children": {
        "domestic_violence": [
            "domestic_violence", "domestic violence", "cruelty", "domestic violence / cruelty",
            "marital cruelty", "domestic abuse", "dowry harassment", "spousal abuse",
            "physical abuse marriage", "mental abuse marriage"
        ],
        "sexual_offenses": [
            "sexual_offenses", "sexual offenses", "sexual offences", "rape", "molestation",
            "stalking", "inappropriate touching", "sexual assault", "harassment",
            "public harassment", "eve teasing", "indecent assault"
        ],
        "child_abuse": [
            "child_abuse", "child abuse", "exploitation", "child abuse / exploitation",
            "pocso", "minor exploitation", "child sexual abuse", "child labour exploitation",
            "harm to minor"
        ]
    },
    "property_crimes": {
        "theft_burglary": [
            "theft_burglary", "theft / burglary", "theft", "burglary", "housebreaking",
            "vehicle theft", "house breaking", "break-in", "break in", "housebreak",
            "night burglary", "residential burglary", "stealing", "auto theft",
            "pickpocketing", "purse snatching", "mobile theft", "shoplifting", "larceny"
        ],
        "robbery_snatching": [
            "robbery_snatching", "robbery / snatching", "robbery", "snatching",
            "chain snatching", "phone snatching", "extortion", "armed robbery",
            "street snatching", "forceful grabbing"
        ],
        "vandalism_arson": [
            "vandalism_arson", "vandalism / arson", "vandalism", "arson", "setting fire",
            "property damage", "destroying public property", "mischief by fire",
            "shop fire", "vehicle burning"
        ]
    },
    "cybercrime": {
        "financial_fraud": [
            "financial_fraud", "financial fraud", "cyber fraud", "phishing",
            "phishing links", "upi scams", "digital arrest", "extortion racket",
            "banking fraud", "online scam", "credit card fraud", "investment scam",
            "unauthorized debit", "qr code scam"
        ],
        "identity_theft": [
            "identity_theft", "identity theft", "fake profile", "fake social media profile",
            "aadhaar fraud", "pan card fraud", "impersonation", "identity spoofing",
            "cloned account"
        ],
        "online_harassment": [
            "online_harassment", "online harassment", "cyberstalking", "morphing photos",
            "morphing", "digital threats", "online blackmail", "cyber harassment",
            "threatening messages"
        ]
    },
    "narcotics": {
        "drug_trafficking": [
            "drug_trafficking", "drug dealing", "drug trafficking / dealing",
            "selling illegal substances", "contraband pills", "peddling",
            "peddling_activity", "seizure", "drug seizure", "ndps seizure",
            "contraband", "contraband seized", "narcotics confiscation", "narcotic seizure",
            "narcotics seizure", "heroin seizure", "charas bust", "ganja recovery",
            "cocaine seizure", "commercial quantity", "recovery", "substance seizure",
            "contraband recovery", "seized", "street peddler", "smuggling", "dealer arrested"
        ],
        "illicit_storage": [
            "illicit_storage", "cultivation", "illicit storage / cultivation",
            "unauthorized holding", "farming banned plants", "banned cultivation",
            "drug warehouse", "storage", "large package holding", "secret stash",
            "od_admission", "overdose", "od", "substance poisoning"
        ]
    },
    "public_disturbance": {
        "rioting": [
            "rioting", "public fights", "rioting / public fights", "gang fights",
            "mobs disrupting", "mob violence", "unlawful assembly", "communal clash",
            "affray", "locality disruption", "street fight"
        ],
        "cheating_forgery": [
            "cheating_forgery", "cheating / forgery", "cheating", "forgery",
            "document-based cheating", "fabricating property deeds", "fake signatures",
            "fake identity cards", "forged documents", "fraudulent deed", "counterfeiting"
        ]
    },
    # Backward compatibility for 'crime'
    "crime": {
        "theft": ["theft", "stealing", "pickpocketing", "purse snatching", "mobile theft", "vehicle theft", "auto theft", "stolen", "petty theft", "shoplifting", "larceny", "snatching", "robbery", "bike theft"],
        "burglary": ["burglary", "house breaking", "house break-in", "break-in", "break in", "housebreak", "house break", "trespass theft", "night burglary", "residential burglary", "commercial break-in", "loot after break"],
        "assault": ["assault", "physical fight", "battery", "beating", "grievous hurt", "quarrel", "scuffle", "weapon attack", "riotous attack", "street violence", "affray", "brawl", "simple hurt"],
        "hit_and_run": ["hit_and_run", "hit & run", "hit and run", "hit-and-run", "accident hit and run", "vehicle collision fleeing", "fled scene accident", "rash driving death", "road accident hit and run", "fatal accident"]
    }
}

DOMAINS_METADATA = {
    "physical_harm": {
        "domain": "physical_harm",
        "name": "Crimes Involving Physical Harm & Violence",
        "color": "#ef4444",
        "icon": "🩸",
        "governing_law": "Chapter VI of Bharatiya Nyaya Sanhita, 2023 (BNS) - Offences Affecting the Human Body (Sec 101 Murder, Sec 115 Hurt, Sec 106 Hit-and-Run, Sec 137 Kidnapping)",
        "required_evidence": "Medical reports (MLC), blood samples, weapons recovered from spot, CCTV footage of assault, eyewitness testimony (under BSA 2023)",
        "emergency_number": "112",
        "categories": {
            "murder": "Murder / Attempt to Murder",
            "assault": "Assault / Hurt",
            "hit_and_run": "Hit and Run",
            "kidnapping": "Kidnapping"
        }
    },
    "women_children": {
        "domain": "women_children",
        "name": "Crimes Against Women and Children",
        "color": "#d946ef",
        "icon": "🛡️",
        "governing_law": "Chapter V of Bharatiya Nyaya Sanhita, 2023 (BNS) - Offences Against Women and Children; POCSO Act (Protection of Children from Sexual Offences Act)",
        "required_evidence": "Audio/video recordings, dynamic electronic communications (chats/messages), medical forensic examinations, magistrate statements (under BSA 2023)",
        "emergency_number": "112 / 1091",
        "categories": {
            "domestic_violence": "Domestic Violence / Cruelty",
            "sexual_offenses": "Sexual Offenses",
            "child_abuse": "Child Abuse / Exploitation"
        }
    },
    "property_crimes": {
        "domain": "property_crimes",
        "name": "Crimes Against Property (Theft & Damage)",
        "color": "#f97316",
        "icon": "📦",
        "governing_law": "Chapter XVII of Bharatiya Nyaya Sanhita, 2023 (BNS) - Offences Against Property (Sec 303 Theft, Sec 304 Snatching, Sec 305 Burglary, Sec 324 Arson/Mischief)",
        "required_evidence": "CCTV footage of break-in, broken locks/fingerprints, proof of ownership of stolen item (under BSA 2023)",
        "emergency_number": "112",
        "categories": {
            "theft_burglary": "Theft / Burglary",
            "robbery_snatching": "Robbery / Snatching",
            "vandalism_arson": "Vandalism / Arson"
        }
    },
    "cybercrime": {
        "domain": "cybercrime",
        "name": "Cybercrimes & Digital Scams",
        "color": "#06b6d4",
        "icon": "💻",
        "governing_law": "Information Technology (IT) Act, 2000 (Sec 66C Identity Theft, Sec 66D Cheating by Impersonation) & BNS Cheating/Fraud sections; Sec 63 BSA electronic certificate",
        "required_evidence": "Screenshots of chats, transaction receipts, bank statements showing debit, IP addresses, emails, Section 63 BSA certificate",
        "emergency_number": "1930 (National Cyber Crime Helpline)",
        "categories": {
            "financial_fraud": "Financial Fraud",
            "identity_theft": "Identity Theft",
            "online_harassment": "Online Harassment"
        }
    },
    "narcotics": {
        "domain": "narcotics",
        "name": "Narcotics & Drug-Related Crimes",
        "color": "#10b981",
        "icon": "🌿",
        "governing_law": "Narcotics Drugs and Psychotropic Substances (NDPS) Act, 1985 (Sec 8/20/21/22/27A/29)",
        "required_evidence": "Physical recovery of contraband, independent panchnama witnesses present during raid, forensic chemical analysis (FSL), digital logs of supply coordination",
        "emergency_number": "112 / 1933",
        "categories": {
            "drug_trafficking": "Drug Trafficking / Dealing",
            "illicit_storage": "Illicit Storage / Cultivation"
        }
    },
    "public_disturbance": {
        "domain": "public_disturbance",
        "name": "Public Disturbance & Scams (Economic/White Collar)",
        "color": "#eab308",
        "icon": "⚠️",
        "governing_law": "Chapter XI of Bharatiya Nyaya Sanhita, 2023 (BNS) - Public Tranquillity (Sec 189 Unlawful Assembly, Sec 191 Rioting); Chapter XVII BNS (Sec 318 Cheating, Sec 336 Forgery)",
        "required_evidence": "Video recordings of mob violence, original forged documents compared against authentic signatures via forensic handwriting experts",
        "emergency_number": "112",
        "categories": {
            "rioting": "Rioting / Public Fights",
            "cheating_forgery": "Cheating / Forgery"
        }
    }
}

class DomainConfig:
    def __init__(self, raw_data: Dict[str, Any], source_path: Optional[str] = None):
        self.raw = raw_data
        self.source_path = source_path
        
        self.domain = raw_data.get("domain", "").lower()
        if not self.domain:
            raise ValueError("DomainConfig must define a 'domain' identifier.")
            
        self.name = raw_data.get("name") or DOMAINS_METADATA.get(self.domain, {}).get("name", self.domain.replace("_", " ").title())
        self.governing_law = raw_data.get("governing_law") or DOMAINS_METADATA.get(self.domain, {}).get("governing_law", "Bharatiya Nyaya Sanhita, 2023 (BNS)")
        self.required_evidence = raw_data.get("required_evidence") or DOMAINS_METADATA.get(self.domain, {}).get("required_evidence", "Physical & digital evidence under Bharatiya Sakshya Adhiniyam, 2023 (BSA)")
        self.color = raw_data.get("color") or DOMAINS_METADATA.get(self.domain, {}).get("color", "#38bdf8")
        self.icon = DOMAINS_METADATA.get(self.domain, {}).get("icon", "🛡️")

        self.geo_unit = raw_data.get("geo_unit", "district").lower()
        self.categories = [str(c).lower() for c in raw_data.get("categories", [])]
        if not self.categories:
            raise ValueError(f"DomainConfig for '{self.domain}' must define at least one category.")
            
        self.aggregation_window = raw_data.get("aggregation_window", "monthly").lower()
        if self.aggregation_window not in ["weekly", "monthly"]:
            self.aggregation_window = "weekly"
            
        self.indicators = raw_data.get("indicators", [])
        if not self.indicators:
            self.indicators = [{"name": "incident_count", "type": "count", "weight": 1.0}]
            
        # Validate indicators
        total_weight = 0.0
        self.indicator_map = {}
        for ind in self.indicators:
            name = ind.get("name")
            weight = float(ind.get("weight", 0.0))
            if name:
                self.indicator_map[name] = ind
                total_weight += weight
            
        if total_weight > 0 and not (0.90 <= total_weight <= 1.10):
            for ind in self.indicators:
                ind["weight"] = round(ind["weight"] / total_weight, 4)
                
        self.scoring_method = raw_data.get("scoring_method", {
            "method": "weighted_composite",
            "normalization": "min_max",
            "thresholds": {"low": 0.3, "medium": 0.6, "high": 0.8}
        })
        self.report_template = raw_data.get("report_template", {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "name": self.name,
            "governing_law": self.governing_law,
            "required_evidence": self.required_evidence,
            "color": self.color,
            "icon": self.icon,
            "geo_unit": self.geo_unit,
            "categories": self.categories,
            "aggregation_window": self.aggregation_window,
            "indicators": self.indicators,
            "scoring_method": self.scoring_method,
            "report_template": self.report_template
        }

    def normalize_category(self, raw_category: Optional[str]) -> Optional[str]:
        """
        Maps a messy or raw category text to one of the configured canonical categories.
        Returns the canonical category string, or None if unmapped.
        """
        if not raw_category:
            return None
        cleaned = str(raw_category).strip().lower()
        if not cleaned:
            return None
            
        # 1. Exact match
        if cleaned in self.categories:
            return cleaned
            
        # 2. Check predefined aliases for this domain
        aliases = CATEGORY_ALIASES.get(self.domain, {})
        
        # Punctuation normalized version
        cleaned_std = cleaned.replace("&", "and").replace("-", " ").replace("_", " ")
        cleaned_std = " ".join(cleaned_std.split())

        for canonical, alias_list in aliases.items():
            if canonical in self.categories:
                # Direct alias check
                if cleaned in alias_list:
                    return canonical
                for alias in alias_list:
                    alias_std = alias.replace("&", "and").replace("-", " ").replace("_", " ")
                    alias_std = " ".join(alias_std.split())
                    if cleaned == alias or cleaned_std == alias_std:
                        return canonical
                for alias in alias_list:
                    alias_std = alias.replace("&", "and").replace("-", " ").replace("_", " ")
                    alias_std = " ".join(alias_std.split())
                    if alias_std in cleaned_std or cleaned_std in alias_std:
                        return canonical
                        
        # 3. Fuzzy substring in configured categories
        for cat in self.categories:
            cat_std = cat.replace("_", " ")
            if cat in cleaned or cleaned in cat or cat_std in cleaned_std or cleaned_std in cat_std:
                return cat
                
        return None

def load_domain_config(filepath_or_dict: Any) -> DomainConfig:
    """
    Loads DomainConfig from a file path (.yaml, .yml, .json) or a dictionary.
    """
    if isinstance(filepath_or_dict, dict):
        return DomainConfig(filepath_or_dict)
        
    path = str(filepath_or_dict)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
        
    with open(path, "r", encoding="utf-8") as f:
        if path.endswith(".json"):
            data = json.load(f)
        elif path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(f)
        else:
            # Try json first, fallback to yaml
            content = f.read()
            try:
                data = json.loads(content)
            except Exception:
                data = yaml.safe_load(content)
                
    return DomainConfig(data, source_path=path)
