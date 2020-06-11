import mercantile
import json
import requests
import numpy as np
import rasterio

from config import (
    EXTENTS,
    IMG_SIZE,
    THRESHOLD,
    TILE_SIZE,
    ZOOM_LEVEL
)

from copy import deepcopy
from io import BytesIO
from model import load_from_path

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

# had to do this because of how we are running the script
WEIGHT_FILE = '/ship_detection/weights/iou_model.hdf5'
WMTS_URL = f"https://tiles1.planet.com/data/v1/PSScene3Band/{{}}/{ZOOM_LEVEL}/{{}}/{{}}.png?api_key={{}}"

class Infer:

    def __init__(self, weight_path=WEIGHT_FILE, credential=None):
        self.weight_path = weight_path
        self.model = self.prepare_model()
        self.credential = credential
        self.planet_downloader = PlanetDownloader(credential)


    def prepare_date(self, date):
        return [f"{date}T00:00:00Z", f"{date}T23:59:59Z"]


    def prepare_model(self):
        return load_from_path(self.weight_path)


    def infer(self, date):
        self.start_date_time, self.end_date_time = self.prepare_date(date)
        detections = list()
        for location, extent  in EXTENTS.items():
            items = self.planet_downloader.search_ids(
                extent, self.start_date_time, self.end_date_time
            )
            for item in items:
                print(f"id: {item['id']}")
                images = self.prepare_dataset(item['tiles'], item['id'])
                if len(images) > 0:
                    predictions = self.model.predict((images / 255.))
                    colms, rows = [elem[1] - elem[0] for elem in item['tiles']]
                    predictions = predictions.reshape(
                        (rows, colms, IMG_SIZE, IMG_SIZE)
                    )
                    images = images.reshape(
                        (rows, colms, IMG_SIZE, IMG_SIZE, 3)
                    )
                    polygons = self.xy_to_latlon(
                        predictions, images, rows, colms, item['coordinates']
                    )
                    detections.extend(polygons)
        return { 'type': 'FeatureCollection', 'features': detections }

    def prepare_dataset(self, tile_range, tile_id):
        x_indices, y_indices = tile_range
        images = list()
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
                images.append(img)
            else:
                # this will be printed in the cloudwatch log.
                print(f"{tile_url} not reachable, with error({status_code})")
        return np.asarray(images)


    def prepare_geojson(self, coordinates):
        geojson = deepcopy(GEOJSON_TEMPLATE)
        geojson['geometry']['coordinates'] = coordinates
        return geojson


    def xy_to_latlon(self, grid_list, images, rows, cols, bounds):
        transform = rasterio.transform.from_bounds(
            *bounds, TILE_SIZE * cols, TILE_SIZE * rows
        )
        polygon_coordinates = list()
        rows, colms, _, _ = np.where(grid_list >= THRESHOLD)
        for row, col in set(zip(rows, colms)):
            segments = (grid_list[row][col] > THRESHOLD).astype('uint8')
            # keeping this for when we need to save images.
            # img = Image.fromarray(images[row][col])
            # draw = ImageDraw.Draw(img)
            for idx, ship in enumerate(regionprops(segments)):
                bbox = ship.bbox
                xs = bbox[::2]
                ys = bbox[1::2]
                # draw.rectangle(
                #     [
                #         (xs[0], ys[0]),
                #         (xs[1], ys[1])
                #     ],
                #     fill ='#ffff33',
                #     outline ='red'
                # )
                lons, lats = rasterio.transform.xy(
                    transform, (col * TILE_SIZE) + xs, (row * TILE_SIZE) + ys
                )
                reformated_bbox = self.planet_downloader.prepare_coordinates(
                    [lons[0], lats[0], lons[1], lats[1]]
                )
                polygon_coordinates.append(
                    self.prepare_geojson(reformated_bbox)
                )
            # img.save(f"{row}_{col}.png")
        return polygon_coordinates
