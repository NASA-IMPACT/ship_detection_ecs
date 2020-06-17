import mercantile
import json
import requests
import numpy as np
import rasterio

from config import (
    CACHE_SITES,
    EXTENTS,
    IMG_SIZE,
    THRESHOLD,
    TILE_SIZE,
    ZOOM_LEVEL
)

from copy import deepcopy
from io import BytesIO
from model import load_from_path, make_model_rcnn, predict_rcnn

from PIL import (
    Image,
    ImageDraw
)

from planet_downloader import PlanetDownloader
from skimage.measure import regionprops

GEOJSON_TEMPLATE = {
    "type": "Feature",
    "properties": {},
    "geometry": {
        "type": "Polygon",
        "coordinates": []
    }
}

SITE_URL = 'https://8ib71h0627.execute-api.us-east-1.amazonaws.com/v1/sites'

# had to do this because of how we are running the script
WEIGHT_FILE = '/ship_detection/weights/iou_model.hdf5'
WMTS_URL = f"https://tiles1.planet.com/data/v1/PSScene3Band/{{}}/{ZOOM_LEVEL}/{{}}/{{}}.png?api_key={{}}"

class Infer:

    def __init__(self, weight_path=WEIGHT_FILE, credential=None):
        self.weight_path = weight_path
        self.model = make_model_rcnn()
        self.credential = credential
        self.planet_downloader = PlanetDownloader(credential)
        self._extents = None

    def prepare_date(self, date):
        return [f"{date}T00:00:00Z", f"{date}T23:59:59Z"]

    def prepare_model(self):
        return load_from_path(self.weight_path)


    def extents(self):
        if not self._extents:
            site_response = requests.get(SITE_URL)
            self._extents = {}
            if site_response.status_code == 200:
                sites = json.loads(site_response.text)['sites']
            else:
                sites = CACHE_SITES
            for site in sites:
                self._extents[site['label']] = site['bounding_box']
        return self._extents


    def infer(self, date, extents=None):
        self.start_date_time, self.end_date_time = self.prepare_date(date)
        location_wise_detections = []
        # saving this method call for when we are ready to do other locations
        # currently only running for sanfran, LA, and NY
        extents = extents or CACHE_SITES # extents or self.extents()
        detection_count = 0
        for extent in extents:
            location = extent['label']
            detections = list()
            scene_ids = list()
            items = self.planet_downloader.search_ids(
                extent['bounding_box'], self.start_date_time, self.end_date_time
            )
            print(f"Total scenes: {len(items)}")
            for item in items:
                print(f"id: {item['id']}, tile range: {item['tiles']}")
                scene_ids.append(item['id'])
                images = self.prepare_dataset(item['tiles'], item['id'])
                predictions = list()
                for image in images:
                    predictions.append(predict_rcnn(self.model, image))
                predictions = np.asarray(predictions)
                columns, rows = [elem[1] - elem[0] for elem in item['tiles']]
                predictions = predictions.reshape(
                    (rows, columns, IMG_SIZE, IMG_SIZE)
                )
                polygons = self.xy_to_latlon(
                    predictions, rows, columns, item['coordinates']
                )
                detection_count += len(polygons)
                detections.extend(polygons)

            location_wise_detections.append({
                'location': location,
                'geojson': {
                    'type': 'FeatureCollection',
                    'features': detections
                },
                'scene_ids': scene_ids
            })

        return (location_wise_detections, detection_count)


    def prepare_dataset(self, tile_range, tile_id):
        x_indices, y_indices = tile_range
        for x_index in list(range(*x_indices)):
            for y_index in list(range(*y_indices)):
                tile_url = WMTS_URL.format(
                    tile_id,
                    x_index,
                    y_index,
                    self.credential
                )
                response = requests.get(tile_url)
                status_code = response.status_code
                if status_code == 200:
                    img = np.asarray(
                      Image.open(BytesIO(response.content)).resize(
                          (IMG_SIZE, IMG_SIZE)
                        ).convert('RGB')
                      )
                    yield np.asarray([img])


    def prepare_geojson(self, coordinates, area):
        geojson = deepcopy(GEOJSON_TEMPLATE)
        geojson['geometry']['coordinates'] = coordinates
        geojson['properties']['area'] = area
        return geojson


    def xy_to_latlon(self, grid_list, rows, cols, bounds):
        transform = rasterio.transform.from_bounds(
            *bounds, TILE_SIZE * cols, TILE_SIZE * rows
        )
        polygon_coordinates = list()
        rows, colms, _, _ = np.where(grid_list >= THRESHOLD)
        for row, col in set(zip(rows, colms)):
            segments = (grid_list[row][col] > THRESHOLD).astype('uint8')
            for idx, ship in enumerate(regionprops(segments)):
                bbox = ship.bbox
                xs = bbox[::2]
                ys = bbox[1::2]
                area = abs(xs[0] - xs[1]) * abs(ys[0] - ys[1])
                lons, lats = rasterio.transform.xy(
                    transform, (col * TILE_SIZE) + xs, (row * TILE_SIZE) + ys
                )
                reformated_bbox = self.planet_downloader.prepare_coordinates(
                    [lons[0], lats[0], lons[1], lats[1]]
                )
                polygon_coordinates.append(
                    self.prepare_geojson(reformated_bbox, area)
                )
        return polygon_coordinates
