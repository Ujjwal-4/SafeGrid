"""
core/tabular_parser.py
Robust CSV and Excel (.xlsx) parser for law enforcement and emergency response logs.
Includes:
- Auto-detection of columns: location, crime category, date/time, source, district, police station.
- Flexible datetime parsing (ISO 8601, standard formats, Excel serial dates).
- Category normalization using domain configuration.
- Row flagging for incomplete/ambiguous rows (instead of dropping them).
"""

import io
import re
import csv
import zipfile
import datetime
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Optional
import math
from core.config_loader import DomainConfig, CATEGORY_ALIASES

# Comprehensive alias lists per field (Requirement 2)
FIELD_ALIASES = {
    "location": [
        "address_text", "address", "location", "place", "incident_address",
        "caller_reported_location", "complaint_summary_location", "scene",
        "spot", "place_of_occurrence", "site", "addr", "incident_location", "crime_location"
    ],
    "category": [
        "crime_type", "category", "type", "offence", "offense", "crime_head",
        "crime_category", "call_nature", "nature_of_complaint", "nature", "charge"
    ],
    "datetime": [
        "occurred_at", "date", "incident_date", "datetime", "incident_datetime",
        "registration_timestamp", "dispatch_datetime", "logged_at", "timestamp",
        "time", "incident_time", "reg_date", "fir_date", "call_date"
    ],
    "lat": [
        "lat", "latitude", "y", "geo_lat", "coord_lat"
    ],
    "lng": [
        "lng", "lon", "longitude", "x", "geo_lng", "coord_lng", "long"
    ],
    "source_ref_id": [
        "source_ref_id", "fir_no", "call_ticket_id", "helpline_ack_no",
        "ref_id", "ref", "ticket_id", "ticket_no", "case_id", "case_no",
        "ack_id", "ack_no", "id"
    ],
    "source": [
        "source", "log_source", "channel", "origin"
    ],
    "district": [
        "district", "district_name", "zone", "division", "jurisdiction_district", "zone_division"
    ],
    "police_station": [
        "police_station", "ps", "thana", "station", "police_stn"
    ],
    "indicator_value": [
        "seizure_volume", "seizure_qty_kg", "estimated_value_inr", "quantity", "value", "metric"
    ]
}

# Secondary regex column name matchers
COLUMN_PATTERNS = {
    "location": [
        r"^(incident_)?address(_text)?$",
        r"^(caller_reported_)?location$",
        r"^(complaint_summary_)?location$",
        r"^(scene|spot|place|site|addr)$",
        r".*address.*",
        r".*location.*",
        r".*spot.*"
    ],
    "category": [
        r"^(crime_)?head$",
        r"^(crime_)?category$",
        r"^call_nature(_code)?$",
        r"^(offence|offense)(_category)?$",
        r"^(crime_)?type$",
        r"^nature(_of_complaint)?$",
        r"^charge$",
        r".*category.*",
        r".*offence.*",
        r".*crime.*"
    ],
    "datetime": [
        r"^(registration_)?timestamp$",
        r"^dispatch_datetime$",
        r"^logged_at$",
        r"^(incident_)?(date|datetime|time)$",
        r"^occurred_at$",
        r"^(reg|fir|call)_(date|datetime|time)$",
        r".*timestamp.*",
        r".*datetime.*"
    ],
    "lat": [
        r"^lat(itude)?$",
        r"^geo_lat$",
        r"^y$"
    ],
    "lng": [
        r"^l(o)?ng(itude)?$",
        r"^lon$",
        r"^geo_lng$",
        r"^x$"
    ],
    "source_ref_id": [
        r"^fir_no$",
        r"^call_ticket_id$",
        r"^helpline_ack_no$",
        r"^(source_)?ref(_id)?$",
        r"^(ticket|complaint|case|ack)_(id|no)$",
        r"^id$"
    ],
    "source": [
        r"^source$",
        r"^log_source$",
        r"^channel$",
        r"^origin$"
    ],
    "district": [
        r"^district(_name)?$",
        r"^zone(_division)?$",
        r"^jurisdiction_district$",
        r"^district$",
        r"^zone$",
        r"^division$"
    ],
    "police_station": [
        r"^police_station$",
        r"^ps$",
        r"^thana$",
        r"^station$",
        r"^police_stn$"
    ],
    "indicator_value": [
        r"^seizure_(qty_)?kg$",
        r"^seizure_volume$",
        r"^estimated_value_inr$",
        r"^quantity$",
        r"^value$"
    ]
}

def parse_excel_xlsx_bytes(file_bytes: bytes) -> Tuple[List[str], List[List[Any]]]:
    """
    Parses an Excel .xlsx file from raw bytes using standard library zipfile and XML parser.
    Works anywhere without requiring openpyxl!
    """
    bio = io.BytesIO(file_bytes)
    with zipfile.ZipFile(bio, 'r') as zf:
        # 1. Load shared strings table if present
        shared_strings = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            ss_xml = zf.read('xl/sharedStrings.xml')
            tree = ET.fromstring(ss_xml)
            # xmlns usually http://schemas.openxmlformats.org/spreadsheetml/2006/main
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in tree.findall('.//ns:si', ns):
                # Text can be in <t> or spread across <r><t>
                t_elems = si.findall('.//ns:t', ns)
                text = "".join([t.text or "" for t in t_elems])
                shared_strings.append(text)
        
        # 2. Find first worksheet
        sheet_path = 'xl/worksheets/sheet1.xml'
        if sheet_path not in zf.namelist():
            for name in zf.namelist():
                if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                    sheet_path = name
                    break
                    
        sheet_xml = zf.read(sheet_path)
        tree = ET.fromstring(sheet_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        raw_rows = []
        for row in tree.findall('.//ns:row', ns):
            current_row = []
            cells = row.findall('.//ns:c', ns)
            # Map by cell reference column index if needed
            for c in cells:
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                is_elem = c.find('.//ns:t', ns)
                
                cell_val = ""
                if t == 's' and v_elem is not None and v_elem.text:
                    idx = int(v_elem.text)
                    if idx < len(shared_strings):
                        cell_val = shared_strings[idx]
                elif t == 'inlineStr' and is_elem is not None:
                    cell_val = is_elem.text or ""
                elif v_elem is not None and v_elem.text:
                    cell_val = v_elem.text
                elif is_elem is not None and is_elem.text:
                    cell_val = is_elem.text
                current_row.append(cell_val)
            if current_row and any(c != "" for c in current_row):
                raw_rows.append(current_row)
                
    if not raw_rows:
        return [], []
        
    headers = [str(h).strip() for h in raw_rows[0]]
    data_rows = raw_rows[1:]
    return headers, data_rows

def parse_csv_bytes(file_bytes: bytes) -> Tuple[List[str], List[List[str]]]:
    """Parses CSV bytes with encoding and delimiter auto-detection."""
    # Attempt decoding with UTF-8, then UTF-8 with BOM, then Latin-1
    text = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
            
    if text is None:
        text = file_bytes.decode('utf-8', errors='replace')
        
    # Auto-detect delimiter
    sample = text[:4096]
    delimiter = ','
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=',;\t|')
        delimiter = dialect.delimiter
    except Exception:
        if '\t' in sample and ',' not in sample:
            delimiter = '\t'
        elif ';' in sample and ',' not in sample:
            delimiter = ';'
            
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = list(reader)
    if not all_rows:
        return [], []
        
    headers = [str(h).strip() for h in all_rows[0]]
    data_rows = [r for r in all_rows[1:] if any(c.strip() for c in r)]
    return headers, data_rows

def auto_detect_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    """
    Matches column headers to standard fields using alias lists and regex fallbacks.
    Returns mapping: field_name -> column_index (or None).
    """
    clean_headers = [str(h).strip().replace('\r', '').replace('\n', '').lower() for h in headers]
    norm_headers = [re.sub(r'[^a-z0-9_]', '_', h) for h in clean_headers]
    
    mapping = {k: None for k in FIELD_ALIASES.keys()}
    used_indices = set()
    
    priority_order = [
        "category",
        "location",
        "datetime",
        "lat",
        "lng",
        "source",
        "source_ref_id",
        "district",
        "police_station",
        "indicator_value"
    ]
    
    # Pass 1: Exact alias matching
    for field in priority_order:
        aliases = FIELD_ALIASES[field]
        for idx, (clean_h, norm_h) in enumerate(zip(clean_headers, norm_headers)):
            if idx in used_indices:
                continue
            if clean_h in aliases or norm_h in aliases:
                mapping[field] = idx
                used_indices.add(idx)
                break
                
    # Pass 2: Word-boundary & regex pattern fallback for unmapped fields
    for field in priority_order:
        if mapping[field] is not None:
            continue
        aliases = FIELD_ALIASES[field]
        patterns = COLUMN_PATTERNS.get(field, [])
        for idx, (clean_h, norm_h) in enumerate(zip(clean_headers, norm_headers)):
            if idx in used_indices:
                continue
            matched = False
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', clean_h) or re.search(r'\b' + re.escape(alias) + r'\b', norm_h):
                    mapping[field] = idx
                    used_indices.add(idx)
                    matched = True
                    break
            if matched:
                continue
            for pat in patterns:
                if re.match(pat, norm_h):
                    mapping[field] = idx
                    used_indices.add(idx)
                    break
                    
    return mapping

def parse_flexible_datetime(dt_val: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses various date/time formats into an ISO 8601 UTC timestamp.
    Handles ISO, YYYY-MM-DD HH:MM, YYYY-MM-DD HH:MM:SS, DD/MM/YYYY, Excel serial numbers, etc.
    Returns: (iso_str, flag_reason).
    If valid: (iso_str, None).
    If missing: (None, "missing date").
    If invalid: (None, "invalid date").
    """
    if dt_val is None:
        return None, "missing date"
        
    dt_str = str(dt_val).strip().replace('\r', '').replace('\n', '')
    if not dt_str or dt_str.lower() in ["none", "null", "nan", "na", "-", "n/a", "nil", ""]:
        return None, "missing date"
        
    # Excel serial number (e.g. 45800 or 45800.5)
    try:
        num = float(dt_str)
        if 10000 < num < 80000:
            excel_base = datetime.datetime(1899, 12, 30)
            parsed_dt = excel_base + datetime.timedelta(days=num)
            return parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), None
    except ValueError:
        pass
        
    # Unix epoch timestamp (seconds or milliseconds)
    if dt_str.isdigit():
        try:
            if len(dt_str) == 10:
                dt = datetime.datetime.fromtimestamp(int(dt_str), tz=datetime.timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), None
            elif len(dt_str) == 13:
                dt = datetime.datetime.fromtimestamp(int(dt_str) / 1000.0, tz=datetime.timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), None
        except Exception:
            pass

    # Normalize ISO suffix
    clean_str = dt_str.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), None
        return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), None
    except Exception:
        pass

    formats = [
        # YYYY-MM-DD formats
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        
        # DD/MM/YYYY and DD-MM-YYYY formats
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y",
        
        # YYYY/MM/DD formats
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        
        # MM/DD/YYYY formats
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%m-%d-%Y %H:%M:%S",
        "%m-%d-%Y %H:%M",
        "%m-%d-%Y",
        
        # 12-hour AM/PM formats
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %I:%M %p",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%d-%m-%Y %I:%M:%S %p",
        "%d-%m-%Y %I:%M %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(dt_str, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), None
        except ValueError:
            continue
            
    return None, "invalid date"

def map_category_with_domain(
    raw_cat: Optional[str],
    domain_config: DomainConfig
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Normalises raw category text against domain config and predefined synonyms.
    Returns: (canonical_category, domain_name, flag_reason)
    """
    if raw_cat is None:
        return None, None, "missing crime type"
        
    cleaned = str(raw_cat).strip()
    if not cleaned or cleaned.lower() in ["none", "null", "nan", "na", "-", ""]:
        return None, None, "missing crime type"
        
    # 1. Try normalizing using the active domain_config
    canonical = domain_config.normalize_category(cleaned)
    if canonical:
        return canonical, domain_config.domain, None
        
    # 2. Cross-domain fallback: check all predefined categories in CATEGORY_ALIASES
    cleaned_lower = cleaned.lower()
    cleaned_std = cleaned_lower.replace("&", "and").replace("-", " ").replace("_", " ")
    cleaned_std = " ".join(cleaned_std.split())
    
    for dom, cat_map in CATEGORY_ALIASES.items():
        for canon, aliases in cat_map.items():
            if cleaned_lower == canon:
                return canon, dom, None
            if cleaned_lower in aliases:
                return canon, dom, None
            for alias in aliases:
                alias_std = alias.replace("&", "and").replace("-", " ").replace("_", " ")
                alias_std = " ".join(alias_std.split())
                if cleaned_std == alias_std or alias_std in cleaned_std or cleaned_std in alias_std:
                    return canon, dom, None
                    
    # 3. No match found
    return None, None, f"unrecognised category: {cleaned}"

def infer_source_from_row(
    row_dict: Dict[str, Any],
    file_name: Optional[str] = None,
    explicit_source: Optional[str] = None
) -> str:
    """Infers the logging source: fir | call_100 | call_1930 | manual_entry."""
    if explicit_source:
        src = str(explicit_source).lower()
        if "fir" in src:
            return "fir"
        if "100" in src or "dial" in src or "pcr" in src:
            return "call_100"
        if "1930" in src or "cyber" in src or "helpline" in src:
            return "call_1930"
        return "manual_entry"
        
    # Check ref ID or row content
    joined_text = " ".join([str(v).lower() for v in row_dict.values()])
    if "fir" in joined_text:
        return "fir"
    if "pcr" in joined_text or "call_100" in joined_text or "ticket" in joined_text:
        return "call_100"
    if "1930" in joined_text or "helpline" in joined_text or "ack-1930" in joined_text:
        return "call_1930"
        
    if file_name:
        fname = file_name.lower()
        if "fir" in fname:
            return "fir"
        if "100" in fname:
            return "call_100"
        if "1930" in fname:
            return "call_1930"
            
    return "manual_entry"

class ParsedTabularData:
    def __init__(
        self,
        headers: List[str],
        column_mapping: Dict[str, Optional[int]],
        valid_rows: List[Dict[str, Any]],
        flagged_rows: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ):
        self.headers = headers
        self.column_mapping = column_mapping
        self.valid_rows = valid_rows
        self.flagged_rows = flagged_rows
        self.metadata = metadata

def parse_tabular_file(
    file_bytes: bytes,
    file_name: str,
    domain_config: DomainConfig
) -> ParsedTabularData:
    """
    Main ingestion function for CSV and Excel files.
    Auto-detects columns, normalizes categories against domain_config,
    flags ambiguous or incomplete rows without dropping them.
    """
    is_excel = file_name.lower().endswith(('.xlsx', '.xlsm'))
    
    if is_excel:
        headers, data_rows = parse_excel_xlsx_bytes(file_bytes)
    else:
        headers, data_rows = parse_csv_bytes(file_bytes)
        
    if not headers or not data_rows:
        return ParsedTabularData(headers, {}, [], [], {"error": "Empty or unreadable file"})
        
    col_map = auto_detect_columns(headers)
    
    loc_idx = col_map.get("location")
    cat_idx = col_map.get("category")
    dt_idx = col_map.get("datetime")
    lat_idx = col_map.get("lat")
    lng_idx = col_map.get("lng")
    src_ref_idx = col_map.get("source_ref_id")
    src_idx = col_map.get("source")
    dist_idx = col_map.get("district")
    ps_idx = col_map.get("police_station")
    ind_val_idx = col_map.get("indicator_value")
    
    valid_rows = []
    flagged_rows = []
    
    for r_idx, row in enumerate(data_rows, start=1):
        # Pad row to match headers count
        padded_row = list(row) + [""] * max(0, len(headers) - len(row))
        row_dict = {headers[i]: padded_row[i] for i in range(len(headers))}
        
        flag_reasons = []
        confidence_penalties = 0.0
        
        # 1. Location check
        address_text = ""
        if loc_idx is not None and loc_idx < len(padded_row):
            address_text = str(padded_row[loc_idx]).strip().replace('\r', '').replace('\n', '')
        if not address_text or len(address_text) < 2 or address_text.lower() in ["none", "null", "nan", "na", "-", ""]:
            flag_reasons.append("missing location")
            confidence_penalties += 0.40

        # Coordinates parsing (lat / lng)
        lat_val = None
        lng_val = None
        if lat_idx is not None and lat_idx < len(padded_row):
            try:
                raw_lat = str(padded_row[lat_idx]).strip()
                v = float(raw_lat)
                if not math.isnan(v) and -90.0 <= v <= 90.0:
                    lat_val = round(v, 6)
            except (ValueError, TypeError):
                lat_val = None

        if lng_idx is not None and lng_idx < len(padded_row):
            try:
                raw_lng = str(padded_row[lng_idx]).strip()
                v = float(raw_lng)
                if not math.isnan(v) and -180.0 <= v <= 180.0:
                    lng_val = round(v, 6)
            except (ValueError, TypeError):
                lng_val = None

        # 2. Category check
        raw_cat = ""
        if cat_idx is not None and cat_idx < len(padded_row):
            raw_cat = str(padded_row[cat_idx]).strip()
            
        canonical_cat, resolved_domain, cat_reason = map_category_with_domain(raw_cat, domain_config)
        if cat_reason:
            flag_reasons.append(cat_reason)
            confidence_penalties += 0.35
            
        # 3. Date / Time check
        occurred_at = None
        raw_dt = None
        if dt_idx is not None and dt_idx < len(padded_row):
            raw_dt = padded_row[dt_idx]
            
        occurred_at, dt_reason = parse_flexible_datetime(raw_dt)
        if dt_reason:
            flag_reasons.append(dt_reason)
            confidence_penalties += 0.25
            
        # 4. Optional fields: district, police station, source ref
        district = ""
        if dist_idx is not None and dist_idx < len(padded_row):
            district = str(padded_row[dist_idx]).strip()
            
        police_station = None
        if ps_idx is not None and ps_idx < len(padded_row):
            ps_val = str(padded_row[ps_idx]).strip()
            if ps_val:
                police_station = ps_val
                
        source_ref_id = None
        if src_ref_idx is not None and src_ref_idx < len(padded_row):
            ref_val = str(padded_row[src_ref_idx]).strip()
            if ref_val:
                source_ref_id = ref_val
                
        # Source inference
        explicit_source = str(padded_row[src_idx]).strip() if src_idx is not None else None
        source = infer_source_from_row(row_dict, file_name, explicit_source)
        
        # Indicator metric extraction
        ind_val = None
        if ind_val_idx is not None and ind_val_idx < len(padded_row):
            try:
                ind_val = float(str(padded_row[ind_val_idx]).strip())
            except ValueError:
                ind_val = None
                
        confidence = max(0.0, round(1.0 - confidence_penalties, 2))
        
        # If required fields have issues, FLAG row instead of dropping it
        if flag_reasons:
            flag_reason_str = flag_reasons[0] if len(flag_reasons) == 1 else ", ".join(flag_reasons)
            flagged_rows.append({
                "row_index": r_idx,
                "flag_reason": flag_reason_str,
                "flag_reasons": flag_reasons,
                "confidence_score": confidence,
                "raw_data": row_dict,
                "partial_mapping": {
                    "address_text": address_text,
                    "category": canonical_cat or raw_cat,
                    "occurred_at": occurred_at,
                    "district": district,
                    "source": source,
                    "lat": lat_val,
                    "lng": lng_val
                }
            })
        else:
            valid_rows.append({
                "row_index": r_idx,
                "raw_data": row_dict,
                "address_text": address_text,
                "category": canonical_cat,
                "domain": resolved_domain or domain_config.domain,
                "occurred_at": occurred_at,
                "district": district,
                "police_station": police_station,
                "source": source,
                "source_ref_id": source_ref_id,
                "indicator_metric": ind_val,
                "lat": lat_val,
                "lng": lng_val
            })
            
    return ParsedTabularData(
        headers=headers,
        column_mapping=col_map,
        valid_rows=valid_rows,
        flagged_rows=flagged_rows,
        metadata={
            "file_name": file_name,
            "total_rows": len(data_rows),
            "valid_count": len(valid_rows),
            "flagged_count": len(flagged_rows),
            "detected_columns": {k: headers[v] for k, v in col_map.items() if v is not None}
        }
    )
