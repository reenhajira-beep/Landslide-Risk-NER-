# =========================================================
# SENTINEL MONITORING LOCATIONS
#
# Weather:
#   Retrieved automatically from live weather server.
#
# latitude / longitude:
#   Used for weather API and Leaflet map.
#
# tilt_deg / vegetation_change_pct / satellite_risk_index:
#   Prepared project/demo GIS features.
#
# Later these three values can also come from
# satellite/GIS services instead of being static.
# =========================================================


LIVE_LOCATIONS = {

    # =====================================================
    # NORTH-EAST INDIA
    # =====================================================

    "GUWAHATI": {
        "name": "Guwahati",
        "state": "Assam",
        "latitude": 26.1445,
        "longitude": 91.7362,
        "tilt_deg": 18.0,
        "vegetation_change_pct": 12.0,
        "satellite_risk_index": 0.35,
    },

    "SHILLONG": {
        "name": "Shillong",
        "state": "Meghalaya",
        "latitude": 25.5788,
        "longitude": 91.8933,
        "tilt_deg": 34.0,
        "vegetation_change_pct": 22.0,
        "satellite_risk_index": 0.68,
    },

    "GANGTOK": {
        "name": "Gangtok",
        "state": "Sikkim",
        "latitude": 27.3389,
        "longitude": 88.6065,
        "tilt_deg": 41.0,
        "vegetation_change_pct": 28.0,
        "satellite_risk_index": 0.76,
    },

    "ITANAGAR": {
        "name": "Itanagar",
        "state": "Arunachal Pradesh",
        "latitude": 27.0844,
        "longitude": 93.6053,
        "tilt_deg": 36.0,
        "vegetation_change_pct": 19.0,
        "satellite_risk_index": 0.63,
    },

    "KOHIMA": {
        "name": "Kohima",
        "state": "Nagaland",
        "latitude": 25.6751,
        "longitude": 94.1086,
        "tilt_deg": 32.0,
        "vegetation_change_pct": 17.0,
        "satellite_risk_index": 0.58,
    },

    "IMPHAL": {
        "name": "Imphal",
        "state": "Manipur",
        "latitude": 24.8170,
        "longitude": 93.9368,
        "tilt_deg": 21.0,
        "vegetation_change_pct": 13.0,
        "satellite_risk_index": 0.42,
    },

    "AIZAWL": {
        "name": "Aizawl",
        "state": "Mizoram",
        "latitude": 23.7271,
        "longitude": 92.7176,
        "tilt_deg": 37.0,
        "vegetation_change_pct": 25.0,
        "satellite_risk_index": 0.69,
    },

    "AGARTALA": {
        "name": "Agartala",
        "state": "Tripura",
        "latitude": 23.8315,
        "longitude": 91.2868,
        "tilt_deg": 14.0,
        "vegetation_change_pct": 8.0,
        "satellite_risk_index": 0.29,
    },


    # =====================================================
    # KERALA
    # =====================================================

    "WAYANAD": {
        "name": "Wayanad",
        "state": "Kerala",
        "latitude": 11.6854,
        "longitude": 76.1320,
        "tilt_deg": 36.0,
        "vegetation_change_pct": 22.0,
        "satellite_risk_index": 0.69,
    },

    "IDUKKI": {
        "name": "Idukki",
        "state": "Kerala",
        "latitude": 9.8494,
        "longitude": 76.9720,
        "tilt_deg": 38.0,
        "vegetation_change_pct": 24.0,
        "satellite_risk_index": 0.72,
    },

    "MUNNAR": {
        "name": "Munnar",
        "state": "Kerala",
        "latitude": 10.0889,
        "longitude": 77.0595,
        "tilt_deg": 42.0,
        "vegetation_change_pct": 26.0,
        "satellite_risk_index": 0.77,
    },

    "KOZHIKODE": {
        "name": "Kozhikode",
        "state": "Kerala",
        "latitude": 11.2588,
        "longitude": 75.7804,
        "tilt_deg": 20.0,
        "vegetation_change_pct": 14.0,
        "satellite_risk_index": 0.40,
    },

    "MALAPPURAM": {
        "name": "Malappuram",
        "state": "Kerala",
        "latitude": 11.0732,
        "longitude": 76.0740,
        "tilt_deg": 26.0,
        "vegetation_change_pct": 17.0,
        "satellite_risk_index": 0.50,
    },

    "THIRUVANANTHAPURAM": {
        "name": "Thiruvananthapuram",
        "state": "Kerala",
        "latitude": 8.5241,
        "longitude": 76.9366,
        "tilt_deg": 12.0,
        "vegetation_change_pct": 10.0,
        "satellite_risk_index": 0.28,
    },


    # =====================================================
    # UTTARAKHAND
    # =====================================================

    "DEHRADUN": {
        "name": "Dehradun",
        "state": "Uttarakhand",
        "latitude": 30.3165,
        "longitude": 78.0322,
        "tilt_deg": 30.0,
        "vegetation_change_pct": 18.0,
        "satellite_risk_index": 0.58,
    },

    "JOSHIMATH": {
        "name": "Joshimath",
        "state": "Uttarakhand",
        "latitude": 30.5553,
        "longitude": 79.5650,
        "tilt_deg": 44.0,
        "vegetation_change_pct": 27.0,
        "satellite_risk_index": 0.82,
    },

    "NAINITAL": {
        "name": "Nainital",
        "state": "Uttarakhand",
        "latitude": 29.3919,
        "longitude": 79.4542,
        "tilt_deg": 39.0,
        "vegetation_change_pct": 23.0,
        "satellite_risk_index": 0.71,
    },


    # =====================================================
    # HIMACHAL PRADESH
    # =====================================================

    "SHIMLA": {
        "name": "Shimla",
        "state": "Himachal Pradesh",
        "latitude": 31.1048,
        "longitude": 77.1734,
        "tilt_deg": 40.0,
        "vegetation_change_pct": 24.0,
        "satellite_risk_index": 0.75,
    },

    "MANALI": {
        "name": "Manali",
        "state": "Himachal Pradesh",
        "latitude": 32.2432,
        "longitude": 77.1892,
        "tilt_deg": 43.0,
        "vegetation_change_pct": 25.0,
        "satellite_risk_index": 0.79,
    },

    "DHARAMSHALA": {
        "name": "Dharamshala",
        "state": "Himachal Pradesh",
        "latitude": 32.2190,
        "longitude": 76.3234,
        "tilt_deg": 38.0,
        "vegetation_change_pct": 20.0,
        "satellite_risk_index": 0.68,
    },


    # =====================================================
    # MAHARASHTRA / WESTERN GHATS
    # =====================================================

    "MAHABALESHWAR": {
        "name": "Mahabaleshwar",
        "state": "Maharashtra",
        "latitude": 17.9307,
        "longitude": 73.6477,
        "tilt_deg": 34.0,
        "vegetation_change_pct": 19.0,
        "satellite_risk_index": 0.61,
    },

    "LONAVALA": {
        "name": "Lonavala",
        "state": "Maharashtra",
        "latitude": 18.7546,
        "longitude": 73.4062,
        "tilt_deg": 31.0,
        "vegetation_change_pct": 17.0,
        "satellite_risk_index": 0.56,
    },


    # =====================================================
    # TAMIL NADU HILL REGIONS
    # =====================================================

    "OOTY": {
        "name": "Ooty",
        "state": "Tamil Nadu",
        "latitude": 11.4102,
        "longitude": 76.6950,
        "tilt_deg": 35.0,
        "vegetation_change_pct": 20.0,
        "satellite_risk_index": 0.63,
    },

    "KODAIKANAL": {
        "name": "Kodaikanal",
        "state": "Tamil Nadu",
        "latitude": 10.2381,
        "longitude": 77.4892,
        "tilt_deg": 37.0,
        "vegetation_change_pct": 21.0,
        "satellite_risk_index": 0.67,
    },


    # =====================================================
    # KARNATAKA WESTERN GHATS
    # =====================================================

    "MADIKERI": {
        "name": "Madikeri",
        "state": "Karnataka",
        "latitude": 12.4244,
        "longitude": 75.7382,
        "tilt_deg": 32.0,
        "vegetation_change_pct": 18.0,
        "satellite_risk_index": 0.59,
    },

    "CHIKMAGALUR": {
        "name": "Chikmagalur",
        "state": "Karnataka",
        "latitude": 13.3161,
        "longitude": 75.7720,
        "tilt_deg": 30.0,
        "vegetation_change_pct": 17.0,
        "satellite_risk_index": 0.55,
    },
}