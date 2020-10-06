ACCOUNT_NUMBER = '853558080719'
CACHE_SITES = [
    {
        'label': 'Los Angeles',
        'bounding_box': [
            -118.54522705078126,
            33.55169563498065,
            -118.11538696289062,
            33.87953701355924
        ]
    },
    {
        'label': 'New York',
        'bounding_box': [
            -74.08802032470703,
            40.556591288249905,
            -73.98571014404297,
            40.63349613448494
        ]
    },
    {
        'label': 'San Francisco',
        'bounding_box': [
            -122.6348876953125,
            37.61314357137536,
            -122.25654602050781,
            37.88081521949766
        ]
    },
    {
       'label': 'Suez Canal',
       'bounding_box': [
           32.212488558892,
           30.3504319202164,
           32.5769732465656,
           31.5788427485226
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
