"""
core/indicator_engine.py
Domain-agnostic indicator scoring, hotspot computation, and report generation.
Calculates:
- Domain indicators for narcotics and crime.
- Multi-criteria weighted threat scores.
- Spatial-temporal hotspot clusters and trend directions (up, down, flat).
- Formatted reports matching DomainConfig report_template.
"""

import math
import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional
from core.models import Incident, Tip, HotspotEntry
from core.config_loader import DomainConfig, DOMAINS_METADATA

CATEGORY_SEVERITY_WEIGHTS = {
    # Physical Harm
    "murder": 1.00,
    "kidnapping": 0.95,
    "assault": 0.85,
    "hit_and_run": 0.75,
    # Women & Children
    "child_abuse": 1.00,
    "sexual_offenses": 0.95,
    "domestic_violence": 0.80,
    # Property Crimes
    "robbery_snatching": 0.85,
    "vandalism_arson": 0.80,
    "theft_burglary": 0.65,
    # Cybercrime
    "financial_fraud": 0.85,
    "identity_theft": 0.75,
    "online_harassment": 0.70,
    # Narcotics
    "drug_trafficking": 0.95,
    "illicit_storage": 0.85,
    # Public Disturbance
    "rioting": 0.90,
    "cheating_forgery": 0.80,
    # Legacy categories
    "burglary": 0.85,
    "theft": 0.50,
    "seizure": 0.85,
    "od_admission": 0.95,
    "peddling_activity": 0.75
}

def calculate_district_indicators(
    incidents: List[Incident],
    tips: List[Tip],
    domain_config: DomainConfig,
    district_areas_sqkm: Optional[Dict[str, float]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Computes domain indicators per district:
    For Narcotics:
    - seizure_volume: sum of seized quantity in kg
    - od_admissions: count of od_admission incidents
    - repeat_offender_density: offender density per sq km
    - verified_tip_density: verified true tips per sq km
    
    For Crime:
    - incident_count: total non-duplicate incidents
    - category_severity: weighted average severity
    - verified_tip_density: verified tips per sq km
    """
    if district_areas_sqkm is None:
        # Default ~45 sq km per urban district
        district_areas_sqkm = defaultdict(lambda: 45.0)
        
    by_district_incidents = defaultdict(list)
    for inc in incidents:
        # Ignore secondary duplicates when computing volume
        if inc.metadata.get("is_duplicate"):
            continue
        if inc.domain == domain_config.domain:
            by_district_incidents[inc.district].append(inc)
            
    by_district_tips = defaultdict(list)
    for t in tips:
        if t.domain == domain_config.domain and t.status == "verified_true":
            by_district_tips[t.district].append(t)
            
    results = {}
    
    # Get all distinct districts
    all_districts = set(list(by_district_incidents.keys()) + list(by_district_tips.keys()))
    if not all_districts:
        all_districts = {"New Delhi", "Central", "North"}
        
    for dist in all_districts:
        dist_incidents = by_district_incidents[dist]
        dist_tips = by_district_tips[dist]
        area = district_areas_sqkm[dist]
        
        indicators_values = {}
        
        if domain_config.domain == "narcotics":
            # 1. seizure_volume
            seizures = [inc for inc in dist_incidents if inc.category in ["seizure", "drug_trafficking"]]
            tot_seizure_vol = 0.0
            for inc in seizures:
                vol = inc.indicators.get("seizure_volume") or inc.metadata.get("indicator_metric") or 1.5
                tot_seizure_vol += float(vol)
            indicators_values["seizure_volume"] = round(tot_seizure_vol, 2)
            
            # 2. od_admissions
            od_count = sum(1 for inc in dist_incidents if inc.category in ["od_admission", "illicit_storage"])
            indicators_values["od_admissions"] = od_count
            
            # 3. repeat_offender_density
            peddling_count = sum(1 for inc in dist_incidents if inc.category in ["peddling_activity", "drug_trafficking"])
            offender_density = round((peddling_count * 1.8) / area, 3)
            indicators_values["repeat_offender_density"] = offender_density
            
            # 4. verified_tip_density
            tip_density = round(len(dist_tips) / area, 3)
            indicators_values["verified_tip_density"] = tip_density
            
        else: # "crime"
            # 1. incident_count
            inc_count = len(dist_incidents)
            indicators_values["incident_count"] = inc_count
            
            # 2. category_severity
            if dist_incidents:
                severity_sum = sum(CATEGORY_SEVERITY_WEIGHTS.get(inc.category, 0.5) for inc in dist_incidents)
                avg_severity = round(severity_sum / len(dist_incidents), 3)
            else:
                avg_severity = 0.0
            indicators_values["category_severity"] = avg_severity
            
            # 3. verified_tip_density
            tip_density = round(len(dist_tips) / area, 3)
            indicators_values["verified_tip_density"] = tip_density
            
        # Calculate composite score based on domain config indicators and weights
        composite_score = 0.0
        for ind in domain_config.indicators:
            name = ind["name"]
            weight = ind["weight"]
            val = indicators_values.get(name, 0.0)
            
            # Normalization scale heuristics
            if name in ["seizure_volume"]:
                norm = min(1.0, val / 30.0)
            elif name in ["od_admissions", "incident_count"]:
                norm = min(1.0, val / 50.0)
            elif name in ["category_severity"]:
                norm = min(1.0, val / 1.0)
            else: # densities
                norm = min(1.0, val / 2.0)
                
            composite_score += norm * weight
            
        composite_score = round(min(1.0, max(0.0, composite_score)), 3)
        
        # Threat level classification
        thresholds = domain_config.scoring_method.get("thresholds", {"low": 0.3, "medium": 0.6, "high": 0.8})
        if composite_score >= thresholds.get("high", 0.8):
            threat_level = "CRITICAL"
        elif composite_score >= thresholds.get("medium", 0.6):
            threat_level = "ELEVATED"
        elif composite_score >= thresholds.get("low", 0.3):
            threat_level = "MODERATE"
        else:
            threat_level = "LOW"
            
        results[dist] = {
            "district": dist,
            "domain": domain_config.domain,
            "indicators": indicators_values,
            "composite_score": composite_score,
            "threat_level": threat_level,
            "total_incidents": len(dist_incidents),
            "verified_tips": len(dist_tips)
        }
        
    return results

def compute_hotspots(
    incidents: List[Incident],
    domain_config: Optional[DomainConfig] = None,
    filter_district: Optional[str] = None,
    filter_category: Optional[str] = None
) -> List[HotspotEntry]:
    """
    Computes Hotspot entries matching Schema 4:
    {
      "district": "string",
      "domain": "physical_harm | women_children | property_crimes | cybercrime | narcotics | public_disturbance",
      "category": "string",
      "lat": "number",
      "lng": "number",
      "frequency": "number",
      "previous_frequency": "number",
      "trend": "up | down | flat",
      "color": "hex string"
    }
    """
    # Group incidents by (district, domain, category)
    if domain_config is not None and domain_config.domain not in ["all", "", None]:
        filtered = [inc for inc in incidents if inc.domain == domain_config.domain and not inc.metadata.get("is_duplicate")]
    else:
        filtered = [inc for inc in incidents if not inc.metadata.get("is_duplicate")]
    
    if filter_district and filter_district.lower() not in ["all", ""]:
        filtered = [inc for inc in filtered if inc.district.lower() == filter_district.lower()]
    if filter_category and filter_category.lower() not in ["all", ""]:
        filtered = [inc for inc in filtered if inc.category.lower() == filter_category.lower()]
        
    groups = defaultdict(list)
    for inc in filtered:
        key = (inc.district, inc.domain, inc.category)
        groups[key].append(inc)
        
    hotspots = []
    
    # Assume 60-40 split between current period and previous period for trend
    for (district, domain, category), group in groups.items():
        if not group:
            continue
            
        # Centroid coordinates
        avg_lat = round(sum(inc.lat for inc in group) / len(group), 6)
        avg_lng = round(sum(inc.lng for inc in group) / len(group), 6)
        
        # Sort by timestamp
        group.sort(key=lambda x: x.occurred_at)
        split_idx = int(len(group) * 0.45)
        
        prev_group = group[:split_idx]
        curr_group = group[split_idx:]
        
        curr_freq = len(curr_group)
        prev_freq = len(prev_group)
        
        # Compute trend
        if prev_freq == 0:
            trend = "up" if curr_freq > 0 else "flat"
        else:
            diff = curr_freq - prev_freq
            pct_change = diff / prev_freq
            if pct_change >= 0.15:
                trend = "up"
            elif pct_change <= -0.15:
                trend = "down"
            else:
                trend = "flat"
                
        domain_color = DOMAINS_METADATA.get(domain, {}).get("color", "#38bdf8")
        hotspots.append(HotspotEntry(
            district=district,
            domain=domain,
            category=category,
            lat=avg_lat,
            lng=avg_lng,
            frequency=curr_freq,
            previous_frequency=prev_freq,
            trend=trend,
            color=domain_color
        ))
        
    # Sort hotspots by frequency descending
    hotspots.sort(key=lambda h: h.frequency, reverse=True)
    return hotspots

def generate_domain_report(
    domain_config: DomainConfig,
    incidents: List[Incident],
    tips: List[Tip],
    format: str = "json"
) -> Dict[str, Any]:
    """Generates intelligence report matching DomainConfig report_template."""
    district_indicators = calculate_district_indicators(incidents, tips, domain_config)
    hotspots = compute_hotspots(incidents, domain_config)
    
    # Sort districts by composite threat score
    ranked_districts = sorted(district_indicators.values(), key=lambda x: x["composite_score"], reverse=True)
    top_threat_districts = ranked_districts[:5]
    
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    
    template = domain_config.report_template
    report_title = template.get("title", f"{domain_config.domain.upper()} Intelligence Threat Report")
    classification = template.get("classification", "LAW ENFORCEMENT SENSITIVE")
    
    report_data = {
        "title": report_title,
        "domain": domain_config.domain,
        "classification": classification,
        "generated_at": now_str,
        "aggregation_period": domain_config.aggregation_window,
        "kpis": {
            "total_incidents_analyzed": len([i for i in incidents if i.domain == domain_config.domain]),
            "active_hotspots_identified": len(hotspots),
            "high_threat_districts": len([d for d in ranked_districts if d["threat_level"] in ["CRITICAL", "ELEVATED"]]),
            "verified_citizen_tips": len([t for t in tips if t.domain == domain_config.domain and t.status == "verified_true"])
        },
        "executive_summary": (
            f"Tactical intelligence analysis for the {domain_config.domain} domain covering "
            f"{len(ranked_districts)} districts. High concentration of risk observed in "
            f"{', '.join([d['district'] for d in top_threat_districts[:3]])}. Priority patrol "
            f"and interdiction directives recommended for flagged hot clusters."
        ),
        "district_risk_rankings": ranked_districts,
        "top_hotspot_clusters": [h.to_dict() for h in hotspots[:10]],
        "operational_recommendations": [
            f"Deploy targeted enforcement teams to top risk districts: {', '.join([d['district'] for d in top_threat_districts[:3]])}.",
            "Increase verification turnaround on high-priority citizen tips within 4 hours.",
            "Cross-reference Dial-100 repeat call coordinates with active FIR registers for pattern analysis.",
            "Focus mobile interdiction patrols during peak temporal activity windows."
        ]
    }
    
    return report_data
