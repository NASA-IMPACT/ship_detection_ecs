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