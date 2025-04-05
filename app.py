from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Layer URLs
ZONING_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/zoning_polys_LUZO/FeatureServer/0/query"
PARCEL_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/Parcel_layers_ArcGISonline_LUZO/FeatureServer/0/query"
LAND_USE_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/land_use_poly_LUZO/FeatureServer/0/query"

@app.route('/')
def home():
    return 'Zoning Lookup API is running! Try /zoning?address=123 Main St, Santa Barbara, CA'

@app.route('/zoning')
def get_zoning():
    address = request.args.get('address')
    if not address:
        return jsonify({"error": "Please provide an address using ?address="}), 400

    # Step 1: Geocode
    geocode_url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    geocode_params = {
        "f": "json",
        "SingleLine": address,
        "outFields": "Match_addr"
    }

    geo_res = requests.get(geocode_url, params=geocode_params).json()
    candidates = geo_res.get('candidates')
    if not candidates:
        return jsonify({"error": "Address not found"}), 404

    location = candidates[0]['location']
    lon = location['x']
    lat = location['y']

    # Step 2: Query Parcel Layer for APN
    apn = ""
    parcel_params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "APN",
        "returnGeometry": "false",
        "f": "json"
    }

    parcel_resp = requests.get(PARCEL_LAYER_URL, params=parcel_params).json()
    parcel_features = parcel_resp.get("features", [])
    if parcel_features:
        apn = parcel_features[0]["attributes"].get("APN", "")

    # Step 3: Query Zoning Layer
    buffer = 0.0002
    zoning_params = {
        "geometry": f"{lon - buffer},{lat - buffer},{lon + buffer},{lat + buffer}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    zoning_resp = requests.get(ZONING_LAYER_URL, params=zoning_params).json()
    zoning_features = zoning_resp.get("features", [])
    zoning_data = zoning_features[0]["attributes"] if zoning_features else {}

    # Step 4: Query Land Use Layer
    land_use_params = {
        "geometry": f"{lon - buffer},{lat - buffer},{lon + buffer},{lat + buffer}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    land_use_resp = requests.get(LAND_USE_LAYER_URL, params=land_use_params).json()
    land_use_features = land_use_resp.get("features", [])
    land_use_data = land_use_features[0]["attributes"] if land_use_features else {}

    # Final response
    return jsonify({
        "input_address": address,
        "latitude": lat,
        "longitude": lon,
        "parcel_apn": apn,
        "zoning_code": zoning_data.get("ZONING", ""),
        "zoning_description": zoning_data.get("ZonDescrip", ""),
        "zoning_class": zoning_data.get("GEN_CLASS", ""),
        "zoning_type": zoning_data.get("GEN_TYPE", ""),
        "land_use_code": land_use_data.get("LAND_USE", ""),
        "land_use_description": land_use_data.get("LU_Descrip", ""),
        "land_use_class": land_use_data.get("GEN_CLASS", ""),
        "land_use_type": land_use_data.get("GEN_TYPE", ""),
        "parcel_acres": land_use_data.get("Acres", ""),
        "urban_status": zoning_data.get("URBAN", ""),
        "general_plan": zoning_data.get("GEN_PLAN", ""),
        "zoning_overlay": zoning_data.get("ZONEMOD", ""),
        "status": "OK" if zoning_features or land_use_features else "No zoning/land use data found"
    })

if __name__ == '__main__':
    app.run(debug=True)


