from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

ZONING_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/zoning_polys_LUZO/FeatureServer/0/query"
PARCEL_LAYER_URL = "https://services8.arcgis.com/s7n9cRiugyMCsR0U/arcgis/rest/services/Parcel_layers_ArcGISonline_LUZO/FeatureServer/0/query"

@app.route('/')
def home():
    return 'Zoning Lookup API is running! Try /zoning?address=123 Main St, Santa Barbara, CA'

@app.route('/zoning')
def get_zoning():
    address = request.args.get('address')
    if not address:
        return jsonify({"error": "Please provide an address using ?address="}), 400

    # Step 1: Geocode address
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

    # Step 1.5: Query APN from parcel layer
    apn = ""
    apn_params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "APN",
        "returnGeometry": "false",
        "f": "json"
    }

    apn_resp = requests.get(PARCEL_LAYER_URL, params=apn_params).json()
    apn_features = apn_resp.get("features", [])
    if apn_features:
        apn = apn_features[0]["attributes"].get("APN", "")

    # Step 2: Query zoning/land use layer
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

    zoning_res = requests.get(ZONING_LAYER_URL, params=zoning_params).json()
    features = zoning_res.get('features', [])
    if not features:
        return jsonify({
            "input_address": address,
            "latitude": lat,
            "longitude": lon,
            "zoning_code": "",
            "parcel_apn": apn,
            "status": "No zoning code found. May be outside the GIS layer."
        })

    attr = features[0]['attributes']

    return jsonify({
        "input_address": address,
        "latitude": lat,
        "longitude": lon,
        "parcel_apn": apn,
        "zoning_code": attr.get("ZONING", ""),
        "zoning_description": attr.get("ZonDescrip", ""),
        "zoning_class": attr.get("GEN_CLASS", ""),
        "zoning_type": attr.get("GEN_TYPE", ""),
        "land_use_code": attr.get("LANDUSE", ""),
        "land_use_description": attr.get("LAND_DESC", ""),
        "urban_status": attr.get("URBAN", ""),
        "general_plan": attr.get("GEN_PLAN", ""),
        "zoning_overlay": attr.get("ZONEMOD", "")
    })

if __name__ == '__main__':
    app.run(debug=True)

