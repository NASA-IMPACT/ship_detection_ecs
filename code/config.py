CACHE_SITES = [
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
            -74.29916381835938,
            40.408267826445226,
            -73.71139526367188,
            40.733730386116875
        ]
    },
    {
        'label': 'San Francisco',
        'bounding_box': [
            -122.958984375,
            37.52279705525959,
            -122.1240234375,
            38.190704293996504
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

