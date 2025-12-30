from __future__ import annotations

import frappe
import requests


# Soil type classifications and their warnings/equipment for WA fencing
SOIL_WARNINGS = {
    "limestone": {
        "warning": "LIMESTONE ZONE - Core drill likely required. Shallow rock expected within 300-500mm.",
        "equipment": ["Core drill", "Rock anchors", "Diamond-tipped auger"],
        "severity": "high",
    },
    "rock": {
        "warning": "ROCK/GRANITE - Core drill required. May need rock anchors for post installation.",
        "equipment": ["Core drill", "Rock anchors", "Hammer drill"],
        "severity": "high",
    },
    "heavy_clay": {
        "warning": "HEAVY CLAY - Difficult digging. Allow extra time. Posts may need deeper footings due to soil movement.",
        "equipment": ["Clay auger", "Post hole digger with clay bit", "Extra concrete"],
        "severity": "medium",
    },
    "reactive_clay": {
        "warning": "REACTIVE CLAY - High soil movement expected. Deeper footings recommended (600mm+). Consider flexible post bases.",
        "equipment": ["Clay auger", "Deeper post holes", "Extra concrete", "Flexible base plates"],
        "severity": "medium",
    },
    "sand": {
        "warning": "SANDY SOIL - Easy digging but posts need proper concrete footings to prevent movement.",
        "equipment": ["Standard auger", "Extra concrete", "Post stabilizers"],
        "severity": "low",
    },
    "sand_over_limestone": {
        "warning": "SAND OVER LIMESTONE - Easy top layer then rock. Core drill on standby. Rock typically at 300-800mm.",
        "equipment": ["Standard auger", "Core drill (standby)", "Rock anchors"],
        "severity": "medium",
    },
    "peat": {
        "warning": "PEAT/WETLAND - Poor drainage, unstable ground. Deeper posts required. May need ground stabilization.",
        "equipment": ["Longer posts", "Concrete collars", "Drainage consideration"],
        "severity": "medium",
    },
    "loam": {
        "warning": None,  # Good soil, no warning needed
        "equipment": ["Standard auger"],
        "severity": "none",
    },
    "sand_over_loam": {
        "warning": None,  # Generally good conditions
        "equipment": ["Standard auger"],
        "severity": "none",
    },
}

# Known geological zones in Western Australia
WA_GEOLOGICAL_ZONES = [
    # Limestone zones
    {
        "name": "Tamala Limestone (Northern Coastal)",
        "region": "Swan Coastal Plain",
        "soil_type": "limestone",
        "lat_min": -32.5, "lat_max": -31.0,
        "lng_min": 115.5, "lng_max": 116.0,
    },
    {
        "name": "Tamala Limestone (Southern Coastal)",
        "region": "Swan Coastal Plain", 
        "soil_type": "limestone",
        "lat_min": -33.5, "lat_max": -32.5,
        "lng_min": 115.3, "lng_max": 115.9,
    },
    {
        "name": "Cottesloe/Quindalup Dunes",
        "region": "Perth Metro Coastal",
        "soil_type": "sand_over_limestone",
        "lat_min": -32.1, "lat_max": -31.75,
        "lng_min": 115.72, "lng_max": 115.78,
    },
    {
        "name": "Spearwood Dunes",
        "region": "Perth Southern Suburbs",
        "soil_type": "sand_over_limestone",
        "lat_min": -32.4, "lat_max": -32.0,
        "lng_min": 115.75, "lng_max": 115.85,
    },
    # Clay zones
    {
        "name": "Guildford Formation",
        "region": "Perth Eastern Suburbs",
        "soil_type": "heavy_clay",
        "lat_min": -32.1, "lat_max": -31.8,
        "lng_min": 115.9, "lng_max": 116.1,
    },
    {
        "name": "Swan Valley Clay",
        "region": "Swan Valley",
        "soil_type": "reactive_clay",
        "lat_min": -31.85, "lat_max": -31.7,
        "lng_min": 115.95, "lng_max": 116.1,
    },
    # Sandy zones (generally safe)
    {
        "name": "Bassendean Sands",
        "region": "Perth Northern Suburbs",
        "soil_type": "sand",
        "lat_min": -31.9, "lat_max": -31.7,
        "lng_min": 115.8, "lng_max": 115.95,
    },
    # Hills / Rock zones
    {
        "name": "Darling Scarp Granite",
        "region": "Perth Hills",
        "soil_type": "rock",
        "lat_min": -32.3, "lat_max": -31.7,
        "lng_min": 116.0, "lng_max": 116.3,
    },
]


@frappe.whitelist()
def get_soil_data(latitude: float, longitude: float) -> dict:
    """
    Fetch soil data and return warnings/equipment recommendations.
    
    Returns:
        dict with soil_type, region, warning, equipment, is_limestone, severity
    """
    lat = float(latitude)
    lng = float(longitude)
    
    result = {
        "soil_type": "",
        "soil_category": "",
        "region": "",
        "zone_name": "",
        "warning": "",
        "equipment": [],
        "is_limestone": False,
        "severity": "none",
    }
    
    # Check known geological zones (fast local check)
    for zone in WA_GEOLOGICAL_ZONES:
        if (zone["lat_min"] <= lat <= zone["lat_max"] and 
            zone["lng_min"] <= lng <= zone["lng_max"]):
            
            soil_cat = zone["soil_type"]
            soil_info = SOIL_WARNINGS.get(soil_cat, {})
            
            result["zone_name"] = zone["name"]
            result["region"] = zone["region"]
            result["soil_category"] = soil_cat
            result["warning"] = soil_info.get("warning", "")
            result["equipment"] = soil_info.get("equipment", [])
            result["severity"] = soil_info.get("severity", "none")
            result["is_limestone"] = soil_cat in ["limestone", "sand_over_limestone", "rock"]
            break
    
    # Try to fetch actual soil data from CSIRO ASRIS for soil type name
    try:
        asris_data = fetch_asris_soil(lat, lng)
        if asris_data and asris_data.get("soil_type"):
            result["soil_type"] = asris_data["soil_type"]
            if not result["region"] and asris_data.get("region"):
                result["region"] = asris_data["region"]
    except Exception as e:
        frappe.log_error(f"ASRIS API error: {e}", "Probuild Soil Lookup")
    
    # If we got soil type from ASRIS but no local zone match, try to classify it
    if result["soil_type"] and not result["soil_category"]:
        result = classify_soil_type(result)
    
    # Fallback region
    if not result["region"]:
        result["region"] = get_generic_region(lat, lng)
    
    # Format equipment as comma-separated string for display
    result["equipment_str"] = ", ".join(result["equipment"]) if result["equipment"] else "Standard equipment"
    
    return result


def classify_soil_type(result: dict) -> dict:
    """Classify ASRIS soil type into our categories and add appropriate warnings."""
    soil_type_lower = result["soil_type"].lower()
    
    # Classification based on common ASRIS soil type names
    if any(x in soil_type_lower for x in ["limestone", "calcareous", "calcrete"]):
        category = "limestone"
    elif any(x in soil_type_lower for x in ["granite", "laterite", "rock", "ironstone"]):
        category = "rock"
    elif any(x in soil_type_lower for x in ["vertosol", "cracking clay", "black soil"]):
        category = "reactive_clay"
    elif any(x in soil_type_lower for x in ["clay", "sodosol"]):
        category = "heavy_clay"
    elif any(x in soil_type_lower for x in ["peat", "hydrosol", "wetland"]):
        category = "peat"
    elif any(x in soil_type_lower for x in ["sand", "arenosol", "podosol"]):
        category = "sand"
    elif any(x in soil_type_lower for x in ["loam", "dermosol", "chromosol"]):
        category = "loam"
    else:
        category = "loam"  # Default to safe
    
    soil_info = SOIL_WARNINGS.get(category, {})
    result["soil_category"] = category
    result["warning"] = soil_info.get("warning", "")
    result["equipment"] = soil_info.get("equipment", [])
    result["severity"] = soil_info.get("severity", "none")
    result["is_limestone"] = category in ["limestone", "sand_over_limestone", "rock"]
    
    return result


def fetch_asris_soil(lat: float, lng: float) -> dict | None:
    """Query CSIRO ASRIS API for soil information."""
    try:
        url = f"https://www.asris.csiro.au/ASRISApi/api/ACLEP/getASC?longitude={lng}&latitude={lat}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                return {
                    "soil_type": data.get("SoilType", data.get("ASCOrder", "")),
                    "region": data.get("SoilRegion", ""),
                }
    except Exception:
        pass
    return None


def get_generic_region(lat: float, lng: float) -> str:
    """Get a generic region name based on coordinates (WA-focused)."""
    if -32.2 <= lat <= -31.6 and 115.7 <= lng <= 116.1:
        return "Perth Metropolitan Area"
    if -33.5 <= lat <= -31.0 and 115.3 <= lng <= 116.2:
        return "Swan Coastal Plain"
    if -33.0 <= lat <= -31.5 and 116.0 <= lng <= 116.5:
        return "Darling Scarp / Perth Hills"
    if -35.0 <= lat <= -33.0 and 115.0 <= lng <= 117.0:
        return "South West WA"
    if -35.0 <= lat <= -14.0 and 113.0 <= lng <= 129.0:
        return "Western Australia"
    return "Australia"
