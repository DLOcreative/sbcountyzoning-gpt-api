from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ✅ Your actual zoning layer endpoint
ZONING_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/zoning_polys_LUZO/FeatureServer/0/query"

@app.route('/')
def home():
    return 'Zoning Lookup API is running! Try /zoning?address=123 Main St, Santa Barbara, CA'

@app.route('/zoning')
def get_zoning():
    address = request.args.get('address')
    if not address:
        return jsonify({"error": "Please provide an address using ?address="}), 400

    # Step 1: Geocode the address
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

    # Step 2: Query zoning API
    zoning_params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    zoning_res = requests.get(ZONING_LAYER_URL, params=zoning_params).json()
    features = zoning_res.get('features', [])
    if not features:
        return jsonify({"zoning": "Not found in zoning layer"}), 404

    attr = features[0]['attributes']

    return jsonify({
    "input_address": address,
    "latitude": lat,
    "longitude": lon,
    "zoning_code": attr.get("ZONE_CODE", "")
})