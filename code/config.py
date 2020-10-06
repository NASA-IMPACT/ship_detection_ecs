CACHE_SITES = [
    {
        'label': 'Beijing',
        'bounding_box': [
            115.84,
            39.62,
            116.85,
            40.22
        ]
    },
    {
        'label': 'Port of Dunkirk',
        'bounding_box': [
            2.008355962,
            50.96553938,
            2.41646888,
            51.08773119
        ]
    },
    {
        'label': 'Port of Ghent',
        'bounding_box': [
            3.64539683,
            51.06663625,
            3.858333337,
            51.28873095
        ]
    },
    {
        'label': 'Los Angeles',
        'bounding_box': [
            -118.67592739,
            33.42673544,
            -117.07333302,
            34.34392384
        ]
    },
    {
        'label': 'New York',
        'bounding_box': [
            -74.43395,
            40.47812,
            -71.74516,
            41.54467
        ]
    },
    {
        'label': 'San Francisco',
        'bounding_box': [
            -122.63570045,
            37.11988178,
            -121.53518996,
            38.35512939
        ]
    },
    {
        'label': 'Tokyo',
        'bounding_box': [
            139.37,
            35.33,
            140.19,
            35.85
        ]
    }
]

EDGE_CROP = 16
EXTENTS = {
    'san_fran': [-123.43, 37.71, -123.30, 37.85]
}
GAUSSIAN_NOISE = 0.1

GEOJSON_TEMPLATE = {
    "type": "Feature",
    "properties": {},
    "geometry": {
        "type": "Polygon",
        "coordinates": []
    }
}

# downsampling in preprocessing
IMG_SIZE = 768

# downsampling inside the network
NET_SCALING = None

THRESHOLD = 0.5
TILE_SIZE = 256
UPSAMPLE_MODE = 'SIMPLE'
WEIGHT_FILE = '../weights/iou_model.hdf5'
ZOOM_LEVEL = 14  # 16 is in pixel resolution == 2.4m

WMTS_URL = f"https://tiles1.planet.com/data/v1/PSScene3Band/{{}}/{ZOOM_LEVEL}/{{}}/{{}}.png?api_key={{}}"

