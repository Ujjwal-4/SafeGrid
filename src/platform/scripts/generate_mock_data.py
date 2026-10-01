#!/usr/bin/env python3
"""
generate_mock_data.py
Generates realistic mock datasets for crime and narcotics intelligence platforms:
1. District indicator time-series (18 districts across 6 months) for narcotics & crime.
2. Raw emergency logs (FIR, Dial-100, 1930) with realistic column names, messy rows,
   and deliberate duplicates to test spatio-temporal deduplication and flagging.
3. Generates both CSV and standard XLSX formats.
"""

import os
import csv
import json
import random
import datetime
import zipfile
import xml.sax.saxutils as saxutils

# Seed for reproducibility
random.seed(42)

DISTRICTS_DATA = [
    {
        "district": "New Delhi",
        "center_lat": 28.6315,
        "center_lng": 77.2167,
        "stations": ["Connaught Place", "Chanakyapuri", "Parliament Street", "Barakhamba Road"],
        "addresses": [
            "Block B, Inner Circle, Connaught Place",
            "Near Shivaji Stadium Metro, New Delhi",
            "Shanti Path, Chanakyapuri",
            "Janpath Market Lane 3, New Delhi",
            "Tolstoy Marg near KG Marg crossing",
            "Mandir Marg, Sector 4, Gole Market"
        ]
    },
    {
        "district": "Central",
        "center_lat": 28.6450,
        "center_lng": 77.2120,
        "stations": ["Paharganj", "Karol Bagh", "Daryaganj", "Kamla Market"],
        "addresses": [
            "Main Bazar, Paharganj, Near New Delhi Railway Station",
            "Ajmal Khan Road, Karol Bagh Market",
            "Ansari Road, Daryaganj",
            "Asaf Ali Road, Turkman Gate",
            "Desh Bandhu Gupta Road, Pahar Ganj",
            "GB Road near Ajmeri Gate"
        ]
    },
    {
        "district": "North",
        "center_lat": 28.6700,
        "center_lng": 77.2180,
        "stations": ["Kotwali", "Kashmere Gate", "Civil Lines", "Timarpur"],
        "addresses": [
            "Chandni Chowk main road, near Fountain",
            "ISBT Kashmere Gate, Departure Block",
            "Mall Road, Civil Lines",
            "Mukherjee Nagar Commercial Complex",
            "Old Delhi Railway Station, Platform 1 Exit",
            "Kashmere Gate Ring Road Flyover"
        ]
    },
    {
        "district": "North West",
        "center_lat": 28.6980,
        "center_lng": 77.1650,
        "stations": ["Model Town", "Ashok Vihar", "Adarsh Nagar", "Mukherjee Nagar"],
        "addresses": [
            "Model Town Part 2, Main Market",
            "Deep Market, Ashok Vihar Phase 2",
            "Near Azadpur Mandi Gate 4",
            "Shalimar Bagh, AA Block Market",
            "GT Karnal Road, Near Jahangirpuri Metro",
            "Ring Road, Netaji Subhash Place"
        ]
    },
    {
        "district": "West",
        "center_lat": 28.6500,
        "center_lng": 77.1200,
        "stations": ["Rajouri Garden", "Punjabi Bagh", "Tilak Nagar", "Janakpuri"],
        "addresses": [
            "Main Ring Road, Rajouri Garden",
            "Club Road Market, Punjabi Bagh",
            "Mall Road, Tilak Nagar Metro Gate 2",
            "District Centre, Janakpuri",
            "Subhash Nagar Market, Block 6",
            "Kirti Nagar Industrial Area, Phase 2"
        ]
    },
    {
        "district": "South West",
        "center_lat": 28.5700,
        "center_lng": 77.0800,
        "stations": ["Vasant Kunj", "Delhi Cantt", "Palam Village", "Najafgarh"],
        "addresses": [
            "Nelson Mandela Marg, Vasant Kunj",
            "Sadhu Vaswani Marg, Delhi Cantt",
            "Palam Colony, Main Palam-Dabri Road",
            "Najafgarh Main Bus Stand",
            "Mahipalpur Bypass near NH-48",
            "Kapashera Border check post"
        ]
    },
    {
        "district": "South",
        "center_lat": 28.5300,
        "center_lng": 77.2100,
        "stations": ["Hauz Khas", "Saket", "Malviya Nagar", "Mehrauli"],
        "addresses": [
            "Hauz Khas Village, Near Tank",
            "Press Enclave Road, Saket District Centre",
            "Shivalik Main Road, Malviya Nagar",
            "Mehrauli-Gurgaon Road, Qutub Metro",
            "SDA Market, Opp IIT Gate",
            "Anupam Cinema Complex, Saket"
        ]
    },
    {
        "district": "South East",
        "center_lat": 28.5600,
        "center_lng": 77.2600,
        "stations": ["Lajpat Nagar", "Kalkaji", "Govindpuri", "Badarpur"],
        "addresses": [
            "Central Market, Lajpat Nagar II",
            "Kalkaji Main Market, D Block",
            "Govindpuri Extension Gali 7",
            "Badarpur Border Mathura Road",
            "Okhla Industrial Area Phase 3",
            "Nehru Place Computer Market, Pragati Tower"
        ]
    },
    {
        "district": "East",
        "center_lat": 28.6300,
        "center_lng": 77.2900,
        "stations": ["Preet Vihar", "Mayur Vihar", "Kalyanpuri", "Mandawali"],
        "addresses": [
            "Vikas Marg, Preet Vihar",
            "Mayur Vihar Phase 1, Pocket 1 Market",
            "Kalyanpuri Block 12, Main Road",
            "Nirman Vihar Metro Station Pillar 54",
            "Patparganj Industrial Area",
            "Laxmi Nagar Commercial Complex"
        ]
    },
    {
        "district": "Shahdara",
        "center_lat": 28.6700,
        "center_lng": 77.2900,
        "stations": ["Shahdara", "Vivek Vihar", "Anand Vihar", "Seemapuri"],
        "addresses": [
            "Grand Trunk Road, Shahdara Chowk",
            "Surajmal Vihar, Near Cross River Mall",
            "ISBT Anand Vihar, Delhi Terminal",
            "Dilshad Garden Pocket B",
            "Seemapuri Main Border",
            "Jhilmil Industrial Area"
        ]
    },
    {
        "district": "North East",
        "center_lat": 28.7000,
        "center_lng": 77.2700,
        "stations": ["Seelampur", "Jafrabad", "Khajuri Khas", "Bhajanpura"],
        "addresses": [
            "Seelampur Market, GT Road",
            "Jafrabad Metro Station Gate 1",
            "Wazirabad Road, Bhajanpura Chowk",
            "Khajuri Khas Chowk",
            "Brijpuri Main Road",
            "Karawal Nagar Chowk"
        ]
    },
    {
        "district": "Rohini",
        "center_lat": 28.7300,
        "center_lng": 77.1100,
        "stations": ["Rohini North", "Rohini South", "Prashant Vihar", "Begumpur"],
        "addresses": [
            "Sector 3 Market, Rohini",
            "Sector 7 Main Road, Rohini",
            "Prashant Vihar Outer Ring Road",
            "Sector 16 Market, Rohini",
            "Rithala Metro Station Area",
            "Sector 24, Deep Vihar, Rohini"
        ]
    },
    {
        "district": "Outer",
        "center_lat": 28.7000,
        "center_lng": 77.0500,
        "stations": ["Paschim Vihar", "Mangolpuri", "Sultanpuri", "Nangloi"],
        "addresses": [
            "Outer Ring Road, Paschim Vihar West",
            "Mangolpuri Industrial Area Phase 1",
            "Sultanpuri Block C Main Road",
            "Rohtak Road, Nangloi Chowk",
            "Peeragarhi Chowk, Rohtak Road",
            "Mundka Metro Station Depot"
        ]
    },
    {
        "district": "Outer North",
        "center_lat": 28.8100,
        "center_lng": 77.1100,
        "stations": ["Narela", "Bawana", "Samaypur Badli", "Shahbad Dairy"],
        "addresses": [
            "Narela Anaj Mandi, Main Gate",
            "Bawana Industrial Area Sector 2",
            "Samaypur Badli Metro Station",
            "Shahbad Dairy Block A",
            "GT Karnal Road, Singhu Border",
            "Holambi Kalan Railway Crossing"
        ]
    },
    {
        "district": "Dwarka",
        "center_lat": 28.5800,
        "center_lng": 77.0500,
        "stations": ["Dwarka North", "Dwarka South", "Sector 23 Dwarka", "Bindapur"],
        "addresses": [
            "Sector 6 Central Market, Dwarka",
            "Sector 12 Metro Station Market",
            "Sector 10 Main Market, Dwarka",
            "Sector 21 Inter State Metro Terminal",
            "Ramphal Chowk, Sector 7 Dwarka",
            "Bindapur Pocket 4 Main Road"
        ]
    },
    {
        "district": "Gurugram East",
        "center_lat": 28.4700,
        "center_lng": 77.0700,
        "stations": ["DLF Phase 1", "Cyber City", "Sushant Lok", "MG Road"],
        "addresses": [
            "Cyber Hub, DLF Cyber City, Sector 24",
            "Galleria Market, DLF Phase 4",
            "MG Road Metro Station area",
            "Golf Course Road, Sector 54",
            "Sikanderpur Metro Station Crossing",
            "Vyapar Kendra, Sushant Lok Phase 1"
        ]
    },
    {
        "district": "Noida Central",
        "center_lat": 28.5700,
        "center_lng": 77.3400,
        "stations": ["Sector 20", "Sector 39", "Sector 58", "Sector 24"],
        "addresses": [
            "Sector 18 Atta Market, Commercial Hub",
            "Sector 62 IT Park near Electronic City",
            "Sector 50 Central Market",
            "Botanical Garden Metro Station interchange",
            "Sector 38A near GIP Mall",
            "Sector 59 Metro Station area"
        ]
    },
    {
        "district": "Faridabad NIT",
        "center_lat": 28.4000,
        "center_lng": 77.3000,
        "stations": ["NIT 1", "NIT 5", "Old Faridabad", "Ballabgarh"],
        "addresses": [
            "NIT 1 Main Market, BK Chowk",
            "NIT 5 Market Road",
            "Neelam Chowk, Bata Road",
            "Mathura Road near Badkhal Flyover",
            "Old Faridabad Railway Road",
            "Ballabgarh Bus Stand, Mathura Road"
        ]
    }
]

MONTHS = [
    "2026-04",
    "2026-05",
    "2026-06",
    "2026-07",
    "2026-08",
    "2026-09"
]

def export_xlsx(headers, rows, filepath):
    """
    Exports data to a valid Excel (.xlsx) file using pure python standard zipfile + xml.
    No external dependencies required!
    """
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>\n'
        '</workbook>'
    )
    
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>\n'
        '</Relationships>'
    )
    
    pkg_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>\n'
        '</Relationships>'
    )
    
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '<Default Extension="xml" ContentType="application/xml"/>\n'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
        '</Types>'
    )
    
    def col_to_letter(col_idx):
        result = ""
        while col_idx >= 0:
            result = chr(ord('A') + (col_idx % 26)) + result
            col_idx = (col_idx // 26) - 1
        return result

    sheet_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>'
    ]
    
    all_data = [headers] + rows
    for r_idx, row in enumerate(all_data, start=1):
        sheet_lines.append(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row):
            col_letter = col_to_letter(c_idx)
            cell_ref = f"{col_letter}{r_idx}"
            if val is None:
                continue
            str_val = str(val)
            escaped = saxutils.escape(str_val)
            # Numeric test
            try:
                float(str_val)
                is_num = not str_val.startswith('0') or str_val == '0' or '.' in str_val
            except ValueError:
                is_num = False
            
            if is_num and len(str_val) < 16:
                sheet_lines.append(f'<c r="{cell_ref}"><v>{escaped}</v></c>')
            else:
                sheet_lines.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
        sheet_lines.append('</row>')
    
    sheet_lines.append('</sheetData></worksheet>')
    sheet_xml = '\n'.join(sheet_lines)
    
    with zipfile.ZipFile(filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', pkg_rels)
        zf.writestr('xl/_rels/workbook.xml.rels', rels_xml)
        zf.writestr('xl/workbook.xml', wb_xml)
        zf.writestr('xl/worksheets/sheet1.xml', sheet_xml)

DOMAINS_TAXONOMY = {
    "physical_harm": {
        "name": "Crimes Involving Physical Harm & Violence",
        "categories": ["murder", "assault", "hit_and_run", "kidnapping"],
        "color": "#ef4444"
    },
    "women_children": {
        "name": "Crimes Against Women and Children",
        "categories": ["domestic_violence", "sexual_offenses", "child_abuse"],
        "color": "#d946ef"
    },
    "property_crimes": {
        "name": "Crimes Against Property",
        "categories": ["theft_burglary", "robbery_snatching", "vandalism_arson"],
        "color": "#f97316"
    },
    "cybercrime": {
        "name": "Cybercrimes & Digital Scams",
        "categories": ["financial_fraud", "identity_theft", "online_harassment"],
        "color": "#06b6d4"
    },
    "narcotics": {
        "name": "Narcotics & Drug-Related Crimes",
        "categories": ["drug_trafficking", "illicit_storage"],
        "color": "#10b981"
    },
    "public_disturbance": {
        "name": "Public Disturbance & Scams",
        "categories": ["rioting", "cheating_forgery"],
        "color": "#eab308"
    }
}

def generate_narcotics_indicators(output_dir):
    """Generates monthly indicators for 18 districts across 6 months for narcotics."""
    filepath = os.path.join(output_dir, "mock_narcotics_indicators.csv")
    headers = [
        "district",
        "month",
        "seizure_volume",
        "od_admissions",
        "repeat_offender_density",
        "verified_tip_density",
        "composite_threat_score"
    ]
    rows = []
    
    for dist in DISTRICTS_DATA:
        name = dist["district"]
        base_risk = 1.6 if name in ["Central", "North East", "Outer North", "Shahdara", "West"] else 0.8
        
        for m_idx, month in enumerate(MONTHS):
            trend = 1.0 + (m_idx * 0.05)
            seizure = round(max(0.5, random.gauss(8.5 * base_risk * trend, 2.5)), 2)
            od = int(max(0, round(random.gauss(6.0 * base_risk * trend, 2.0))))
            offenders = round(max(0.1, random.gauss(2.2 * base_risk, 0.4)), 2)
            tips = round(max(0.05, random.gauss(1.5 * base_risk * trend, 0.3)), 2)
            norm_score = round(min(1.0, (seizure / 25.0)*0.35 + (od / 18.0)*0.30 + (offenders / 5.0)*0.20 + (tips / 4.0)*0.15), 3)
            
            rows.append([
                name,
                month,
                seizure,
                od,
                offenders,
                tips,
                norm_score
            ])
            
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} narcotics indicator rows -> {filepath}")
    return filepath

def generate_standard_domain_indicators(output_dir, domain_key: str):
    """Generates monthly indicators for any standard domain (incident_count, category_severity, verified_tip_density)."""
    filepath = os.path.join(output_dir, f"mock_{domain_key}_indicators.csv")
    headers = [
        "district",
        "month",
        "incident_count",
        "category_severity",
        "verified_tip_density",
        "composite_threat_score"
    ]
    rows = []
    
    for dist in DISTRICTS_DATA:
        name = dist["district"]
        base_risk = 1.4 if name in ["North", "Rohini", "Outer", "South East", "Central", "West"] else 0.85
        
        for m_idx, month in enumerate(MONTHS):
            incidents = int(max(10, round(random.gauss(75.0 * base_risk, 15.0))))
            severity = round(max(0.35, min(0.95, random.gauss(0.70 * base_risk, 0.08))), 3)
            tips = round(max(0.1, random.gauss(2.5 * base_risk, 0.6)), 2)
            norm_score = round(min(1.0, (incidents / 160.0)*0.40 + (severity / 1.0)*0.40 + (tips / 5.0)*0.20), 3)
            
            rows.append([
                name,
                month,
                incidents,
                severity,
                tips,
                norm_score
            ])
            
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} {domain_key} indicator rows -> {filepath}")
    return filepath

def generate_raw_operational_logs(output_dir):
    """
    Generates realistic operational log datasets covering all 6 statutory domains:
    - FIR police station registrations (CSV and XLSX)
    - Dial-100 emergency call records
    - 1930 Cyber & Helpline logs
    Includes real addresses, coordinates, deliberate duplicates, and malformed rows.
    """
    fir_rows = []
    fir_headers = [
        "FIR_No",
        "District_Name",
        "Police_Station",
        "Crime_Head",
        "Incident_Address",
        "Registration_Timestamp",
        "Seizure_Qty_Kg",
        "Investigating_Officer"
    ]
    
    dial100_rows = []
    dial100_headers = [
        "Call_Ticket_ID",
        "Zone_Division",
        "Caller_Reported_Location",
        "Call_Nature_Code",
        "Dispatch_DateTime",
        "Caller_Phone_Masked",
        "PCR_Unit_Assigned"
    ]
    
    call1930_rows = []
    call1930_headers = [
        "Helpline_Ack_No",
        "Jurisdiction_District",
        "Complaint_Summary_Location",
        "Offence_Category",
        "Logged_At",
        "Suspect_Details",
        "Estimated_Value_INR"
    ]
    
    domain_keys = list(DOMAINS_TAXONOMY.keys())
    
    fir_counter = 1001
    call_counter = 80001
    helpline_counter = 5001
    paired_duplicates = []
    
    for i in range(180):
        dist = random.choice(DISTRICTS_DATA)
        district_name = dist["district"]
        ps = random.choice(dist["stations"])
        addr = random.choice(dist["addresses"])
        
        domain = domain_keys[i % len(domain_keys)]
        category = random.choice(DOMAINS_TAXONOMY[domain]["categories"])
        
        day = random.randint(1, 28)
        month = random.randint(5, 9)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        dt = datetime.datetime(2026, month, day, hour, minute, 0)
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        seizure_kg = round(random.uniform(0.5, 12.0), 2) if category in ["drug_trafficking", "illicit_storage"] else 0.0
        officer = f"SI {random.choice(['Sharma', 'Verma', 'Singh', 'Yadav', 'Meena', 'Khan', 'Patel', 'Das'])}"
        fir_no = f"FIR-{district_name[:3].upper()}-2026-{fir_counter:04d}"
        fir_counter += 1
        
        fir_rows.append([
            fir_no,
            district_name,
            ps,
            category,
            addr,
            dt_str,
            seizure_kg,
            officer
        ])
        
        # Paired Dial-100 duplicate (every 5th incident)
        if i % 5 == 0:
            call_dt = dt - datetime.timedelta(minutes=random.randint(30, 120))
            call_id = f"PCR-DL-{call_counter:06d}"
            call_counter += 1
            dial100_rows.append([
                call_id,
                district_name,
                addr,
                category,
                call_dt.strftime("%Y-%m-%d %H:%M:%S"),
                f"98765{random.randint(10000, 99999)}",
                f"EAGLE-{random.randint(11, 88)}"
            ])
            paired_duplicates.append((call_id, fir_no, addr, category, call_dt.isoformat(), dt.isoformat()))
        else:
            stand_dt = datetime.datetime(2026, random.randint(5, 9), random.randint(1, 28), random.randint(0, 23), random.randint(0, 59))
            stand_domain = random.choice(["physical_harm", "property_crimes", "women_children", "public_disturbance"])
            stand_cat = random.choice(DOMAINS_TAXONOMY[stand_domain]["categories"])
            stand_addr = random.choice(dist["addresses"])
            dial100_rows.append([
                f"PCR-DL-{call_counter:06d}",
                district_name,
                stand_addr,
                stand_cat,
                stand_dt.strftime("%Y-%m-%d %H:%M:%S"),
                f"98110{random.randint(10000, 99999)}",
                f"COMMANDO-{random.randint(10, 50)}"
            ])
            call_counter += 1
            
        # 1930 Cyber / Narcotics helpline call
        if i % 3 == 0:
            h_dt = datetime.datetime(2026, random.randint(5, 9), random.randint(1, 28), random.randint(0, 23), random.randint(0, 59))
            h_domain = random.choice(["cybercrime", "narcotics", "public_disturbance"])
            h_cat = random.choice(DOMAINS_TAXONOMY[h_domain]["categories"])
            call1930_rows.append([
                f"ACK-1930-{helpline_counter:05d}",
                district_name,
                f"Digital incident / transfer near {addr}",
                h_cat,
                h_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "Suspect tracked via IP & transaction trace",
                random.randint(15000, 250000)
            ])
            helpline_counter += 1
            
    # Intentional malformed rows for flagging test
    fir_rows.append([
        "FIR-MAL-2026-9001",
        "Central",
        "Paharganj",
        "murder",
        "",  # Missing address!
        "2026-07-15 14:20:00",
        0.0,
        "SI Sharma"
    ])
    fir_rows.append([
        "FIR-MAL-2026-9002",
        "Unknown_District_ZZZ",
        "Station X",
        "suspicious_unregistered_activity",  # Unknown category!
        "Near unnamed roundabout",
        "2026-08-01 10:00:00",
        0.0,
        "SI Verma"
    ])
    fir_rows.append([
        "FIR-MAL-2026-9003",
        "North",
        "Kotwali",
        "assault",
        "Chandni Chowk Main Gate",
        "INVALID_DATE_FORMAT_TEXT",  # Bad date!
        0.0,
        "SI Singh"
    ])
    
    fir_csv_path = os.path.join(output_dir, "mock_fir_sample.csv")
    with open(fir_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fir_headers)
        writer.writerows(fir_rows)
        
    dial100_path = os.path.join(output_dir, "mock_dial100_logs.csv")
    with open(dial100_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(dial100_headers)
        writer.writerows(dial100_rows)
        
    call1930_path = os.path.join(output_dir, "mock_1930_cyber_narcotics.csv")
    with open(call1930_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(call1930_headers)
        writer.writerows(call1930_rows)
        
    fir_xlsx_path = os.path.join(output_dir, "mock_fir_sample.xlsx")
    export_xlsx(fir_headers, fir_rows, fir_xlsx_path)
    
    print(f"Generated FIR sample ({len(fir_rows)} rows) -> {fir_csv_path} & {fir_xlsx_path}")
    print(f"Generated Dial-100 logs ({len(dial100_rows)} rows) -> {dial100_path}")
    print(f"Generated 1930 helpline logs ({len(call1930_rows)} rows) -> {call1930_path}")
    print(f"Includes {len(paired_duplicates)} intentional spatiotemporal duplicate pairs!")
    
    dupes_meta_path = os.path.join(output_dir, "paired_duplicates_meta.json")
    with open(dupes_meta_path, "w", encoding="utf-8") as f:
        json.dump(paired_duplicates, f, indent=2)

def seed_platform_database(output_dir):
    """
    Populates data/platform.sqlite with rich, realistic incidents and tips
    covering all 6 statutory domains across all 18 districts.
    """
    import sqlite3
    import uuid
    import hashlib
    
    db_path = os.path.join(output_dir, "platform.sqlite")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. Create tables if not exist
    c.execute("""
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
    c.execute("""
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            badge_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            district TEXT,
            password_hash TEXT NOT NULL
        )
    """)
    
    # Clean old incidents and tips to prevent schema mismatch
    c.execute("DELETE FROM incidents")
    c.execute("DELETE FROM tips")
    
    # 2. Seed Users
    def h(pwd):
        return hashlib.sha256(pwd.encode('utf-8')).hexdigest()
        
    users = [
        ("usr-adm-01", "admin", "System Administrator", "supervisor", None, h("admin")),
        ("usr-adm-02", "ADMIN-001", "Chief Admin Officer", "supervisor", None, h("admin_pass")),
        ("usr-sup-01", "SUPER-101", "Supervisor Rao", "supervisor", None, h("supervisor_pass")),
        ("usr-off-01", "OFFICER-001", "Inspector Sharma", "officer", "New Delhi", h("officer_pass")),
        ("usr-off-02", "OFFICER-002", "Sub-Inspector Verma", "officer", "Central", h("officer_pass"))
    ]
    for uid, badge, name, role, dist, pwd_h in users:
        c.execute("""
            INSERT OR REPLACE INTO users (id, badge_id, name, role, district, password_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (uid, badge, name, role, dist, pwd_h))
        
    # 3. Seed Incidents across all 6 statutory domains
    domain_keys = list(DOMAINS_TAXONOMY.keys())
    sources = ["FIR", "call_100", "call_1930"]
    
    incidents_to_insert = []
    
    # For each district, generate incidents for all domains
    for dist in DISTRICTS_DATA:
        d_name = dist["district"]
        c_lat = dist["center_lat"]
        c_lng = dist["center_lng"]
        stations = dist["stations"]
        addresses = dist["addresses"]
        
        for dom_key in domain_keys:
            dom_info = DOMAINS_TAXONOMY[dom_key]
            cats = dom_info["categories"]
            
            # Number of incidents per district per domain: between 6 and 14
            count = random.randint(7, 13)
            for _ in range(count):
                cat = random.choice(cats)
                station = random.choice(stations)
                base_addr = random.choice(addresses)
                
                # Settle jittered coordinates within ~1.5 km
                lat = round(c_lat + random.uniform(-0.018, 0.018), 6)
                lng = round(c_lng + random.uniform(-0.018, 0.018), 6)
                
                # Timestamp between May and late September 2026
                month = random.randint(5, 9)
                day = random.randint(1, 28)
                hour = random.randint(0, 23)
                minute = random.randint(0, 59)
                dt = datetime.datetime(2026, month, day, hour, minute, 0, tzinfo=datetime.timezone.utc)
                iso_ts = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                src = random.choice(sources)
                ref_id = f"{src[:3].upper()}-{d_name[:3].upper()}-{random.randint(10000, 99999)}"
                
                ind_map = {}
                if dom_key == "narcotics":
                    ind_map["seizure_volume"] = round(random.uniform(0.5, 10.0), 2)
                else:
                    ind_map["category_severity"] = round(random.uniform(0.5, 1.0), 2)
                    
                inc_id = str(uuid.uuid4())
                meta = {"geocoded_source": "seed_geolocated", "district": d_name}
                
                incidents_to_insert.append((
                    inc_id,
                    dom_key,
                    cat,
                    src,
                    ref_id,
                    d_name,
                    station,
                    lat,
                    lng,
                    base_addr,
                    iso_ts,
                    iso_ts,
                    json.dumps(ind_map),
                    json.dumps(meta)
                ))
                
    c.executemany("""
        INSERT INTO incidents (
            id, domain, category, source, source_ref_id, district, police_station,
            lat, lng, address_text, occurred_at, created_at, indicators_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, incidents_to_insert)
    
    # 4. Seed Tips across all 6 statutory domains
    sample_descriptions = {
        "physical_harm": [
            "Frequent late-night violent brawls with sharp weapons observed behind market area.",
            "Hit-and-run incident involving dark SUV fleeing towards ring road at high speed.",
            "Suspicious gathering threatening local shopkeepers with physical violence."
        ],
        "women_children": [
            "Continuous domestic violence and severe distress calls heard from 3rd floor apartment.",
            "Group of youths harassing female commuters near metro station gate 2 after 8 PM.",
            "Suspicious person attempting to bait and photograph school children near bus stop."
        ],
        "property_crimes": [
            "Two men with bolt cutters observed inspecting parked motorcycles in residential colony.",
            "Shops broken into overnight; cash drawer and electronics stolen.",
            "Snatchers on black motorbike targeting pedestrians near service lane."
        ],
        "cybercrime": [
            "Fake call center operating from rented apartment running digital arrest scams.",
            "Phishing WhatsApp messages impersonating bank officials with APK malicious links.",
            "Extortion scam threatening seniors via hacked social media accounts."
        ],
        "narcotics": [
            "Suspects distributing contraband packets from tea stall near local bus terminus.",
            "Large supply stash suspected in locked godown with late-night courier visits.",
            "Repeat street peddlers selling synthetic contraband to college students."
        ],
        "public_disturbance": [
            "Organized mob creating unlawful assembly and damaging public street lights.",
            "Fraudulent property broker operating with fake land ownership documents.",
            "Violent clash between two opposing street groups disrupting traffic."
        ]
    }
    
    tips_to_insert = []
    statuses = ["verified_true", "verified_true", "pending", "verified_false", "pending"]
    
    for dist in DISTRICTS_DATA[:12]:
        d_name = dist["district"]
        c_lat = dist["center_lat"]
        c_lng = dist["center_lng"]
        
        for dom_key in domain_keys:
            cat = random.choice(DOMAINS_TAXONOMY[dom_key]["categories"])
            desc = random.choice(sample_descriptions[dom_key])
            stat = random.choice(statuses)
            
            t_lat = round(c_lat + random.uniform(-0.015, 0.015), 6)
            t_lng = round(c_lng + random.uniform(-0.015, 0.015), 6)
            
            now_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=random.randint(1, 10))
            ts = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            verifier = "Inspector Sharma (OFFICER-001)" if stat != "pending" else None
            v_ts = ts if stat != "pending" else None
            
            tip_id = str(uuid.uuid4())
            is_urgent = 1 if random.random() < 0.25 else 0
            is_high_pri = 1 if stat == "verified_true" or random.random() < 0.3 else 0
            
            tips_to_insert.append((
                tip_id,
                dom_key,
                cat,
                d_name,
                desc,
                None,
                t_lat,
                t_lng,
                stat,
                is_high_pri,
                is_urgent,
                ts,
                verifier,
                v_ts
            ))
            
    c.executemany("""
        INSERT INTO tips (
            id, domain, category, district, description, photo_url,
            lat, lng, status, is_high_priority, is_urgent, created_at, verified_by, verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tips_to_insert)
    
    conn.commit()
    conn.close()
    print(f"Successfully seeded database -> {db_path} ({len(incidents_to_insert)} incidents, {len(tips_to_insert)} tips across all 6 domains)")

def main():
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate indicator CSVs for all 6 statutory domains + legacy crime
    generate_narcotics_indicators(output_dir)
    for dom in ["physical_harm", "women_children", "property_crimes", "cybercrime", "public_disturbance", "crime"]:
        generate_standard_domain_indicators(output_dir, dom)
        
    generate_raw_operational_logs(output_dir)
    seed_platform_database(output_dir)
    print("Multi-domain mock data generation & database seeding completed successfully!")

if __name__ == "__main__":
    main()
