from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

ZONING_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/zoning_polys_LUZO/FeatureServer/0/query"

@app.route('/')
def home():
    return 'Zoning Lookup API is running! Try /zoning?address=123 Main St, Santa Barbara, CA'

@app.route('/zoning')
def get_zoning():
    address = request.args.get('address')
    if not address:
        return jsonify({"error": "Please provide an address using ?address="}), 400

    # Step 1: Geocode the address using ArcGIS
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

    # Step 2: Query zoning API using a buffered bounding box
    buffer = 0.0002  # ~20 meters
    zoning_params = {
        "geometry": f"{lon - buffer},{lat - buffer},{lon + buffer},{lat + buffer}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json"
    }

    zoning_res = requests.get(ZONING_LAYER_URL, params=zoning_params).json()
    features = zoning_res.get('features', [])
    if not features:
        return jsonify({
            "input_address": address,
            "latitude": lat,
            "longitude": lon,
            "zoning_code": "",
            "status": "No zoning code found. This may be outside the GIS layer coverage."
        }), 200

    attr = features[0]['attributes']

    return jsonify({
        "input_address": address,
        "latitude": lat,
        "longitude": lon,
        "zoning_code": attr.get("ZONING", ""),
        "zoning_description": attr.get("ZonDescrip", ""),
        "zoning_class": attr.get("GEN_CLASS", ""),
        "zoning_type": attr.get("GEN_TYPE", ""),
        "parcel_apn": attr.get("APN", ""),
        "land_use_code": attr.get("LANDUSE", ""),
        "land_use_description": attr.get("LAND_DESC", ""),
        "urban_status": attr.get("URBAN", ""),
        "general_plan": attr.get("GEN_PLAN", ""),
        "zoning_overlay": attr.get("ZONEMOD", "")
    })

if __name__ == '__main__':
    app.run(debug=True)
