import math
import mercantile
import json
import requests
import numpy as np
import rasterio
import tensorflow as tf

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

IMGS_PER_GPU = 32

SITE_URL = 'https://8ib71h0627.execute-api.us-east-1.amazonaws.com/v1/sites'

# had to do this because of how we are running the script
WEIGHT_FILE = '../weights/iou_model.hdf5'
WMTS_URL = f"https://tiles1.planet.com/data/v1/PSScene3Band/{{}}/{ZOOM_LEVEL}/{{}}/{{}}.png?api_key={{}}"

class Infer:

    def __init__(self, weight_path=WEIGHT_FILE, credential=None):
        """Initializer

        Args:
            weight_path (string, optional): Location of model weight file
            credential (None, optional): API credential to Planet
        """
        self.weight_path = weight_path
        self.model = make_model_rcnn(IMGS_PER_GPU)
        self.credential = credential
        self.planet_downloader = PlanetDownloader(credential)
        self._extents = None
        print('gpu available:', tf.test.is_gpu_available())

    def prepare_date(self, date):
        """Add time information to passed date.

        Args:
            date (string): 'yyyy-mm-dd' formated date string

        Eg:
            start_datetime, end_datetime = self.prepare_date('2020-03-01')
            start_datetime = '2020-03-01T00:00:00Z"'
            end_datetime = '2020-03-01T23:59:59Z'
        Returns:
            list: [start date time, end date time]
        """
        return f"{date}T00:00:00Z", f"{date}T23:59:59Z"

    def prepare_model(self):
        """Prepare Machine Learning model

        Returns:
            keras.models.Model: keras model loaded from provided path
        """
        return load_from_path(self.weight_path)


    def extents(self):
        """
            Defines extents based on Area of Intrests defined in COVID Dashboard

        Returns:
            TYPE: list of extents read from the SITE_URL
        """
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


    def list_scenes(self, date):
        """
            List planetscope scene_ids for a given date

        Args:
            date (string): date in the format 'yyyy-mm-dd'
        """
        self.start_date_time, self.end_date_time = self.prepare_date(date)
        location_wise_detections = []
        # saving this method call for when we are ready to do other locations
        # currently only running for sanfran, LA, and NY
        extents = self._extents or CACHE_SITES # extents or self.extents()
        detection_count = 0
        for extent in extents:
            location = extent['label']
            items = self.planet_downloader.search_ids(
                extent['bounding_box'], self.start_date_time, self.end_date_time
            )
            print(date, location, [item['id'] for item in items])


    def calculate_geojson(self, predictions, bounding_boxes):
        """
            Calculate the geojson based on the bounding box, and x, y coordinates

        Args:
            predictions (list): List of predictions (masks of ships)
            bounding_boxes (list): list of boundingboxes for the tiles on which
            inference was ran

        Returns:
            TYPE: List of geojsons
        """
        geojsons = list()
        for index, pred in enumerate(predictions):
            geojsons.extend(
                self.xy_to_latlon(np.asarray(pred), bounding_boxes[index])
            )
        return geojsons


    def infer(self, date, extents=None):
        """
            Infer based on the extents provided or on the cached extents

        Args:
            date (str): date in 'yyyy-mm-dd' format
            extents (None, optional): list of extents in [left, bottom, right, top] format

        Returns:
            dictionary: location wise detections, and total number of detections
        """
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
                indices = self.prepare_indices(item['tiles'])
                length = len(indices)
                image_group = self.prepare_dataset(indices, item['id'])
                print('total length:', length)
                predictions = list()
                for index, (imgs, bounding_boxes) in enumerate(image_group):
                    print(index)
                    preds = predict_rcnn(self.model, imgs)
                    predictions.extend(self.calculate_geojson(preds, bounding_boxes))
                    preds = []
                # for memory management
                del(image_group)
                predictions = predictions[:length]
                detection_count += len(predictions)
                detections.extend(predictions)

            location_wise_detections.append({
                'location': location,
                'geojson': {
                    'type': 'FeatureCollection',
                    'features': detections
                },
                'scene_ids': scene_ids
            })

        return location_wise_detections, detection_count


    def augment_indices(self, indices):
        """
            Make sure the list of indices contains total number of elements
            in factors of IMGS_PER_GPU

        Args:
            indices (TYPE): list of indices [[x_index, y_index]]

        Returns:
            list: List of augmented x, y indices.
        """
        length = len(indices)
        diff = math.ceil(length / IMGS_PER_GPU) * IMGS_PER_GPU - length
        indices += indices[0:diff]
        return indices


    def prepare_indices(self, tile_range):
        """
            Prepare list of indices for the provided x, y ranges of tiles

        Args:
            tile_range (list): [[x_min, x_max], [y_min, y_max]]

        Returns:
            list: list of x, y indices expanding from min to max
        """
        x_indices, y_indices = tile_range
        indices = list()
        for x_index in range(*x_indices):
            for y_index in range(*y_indices):
                indices.append((x_index, y_index))
        return indices


    def prepare_dataset(self, indices, scene_id):
        """
            prepare the images to be infered on for a tile.

        Args:
            indices (list): list of x, y indices
            scene_id (str): scene_id on which to iterate

        Yields:
            TYPE: Description
        """
        indices = self.augment_indices(indices)

        images = list()
        bounding_boxes = list()
        for x_index, y_index in indices:
            tile_url = WMTS_URL.format(
                scene_id,
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
                bounding_box = mercantile.bounds(x_index, y_index, ZOOM_LEVEL)
                bounding_boxes.append([
                    bounding_box.west,
                    bounding_box.south,
                    bounding_box.east,
                    bounding_box.north
                ])
            length = len(images)
            if length == IMGS_PER_GPU:
                yield images, bounding_boxes
                images = []
                bounding_boxes = []


    def prepare_geojson(self, coordinates, area):
        """
            Prepare the final geojson for the coordinate and area passed

        Args:
            coordinates (list): list of coordinate
            area (int): rounded up area

        Returns:
            dict: dictionary version of the proper geojson for a single detection
        """
        geojson = deepcopy(GEOJSON_TEMPLATE)
        geojson['geometry']['coordinates'] = coordinates
        geojson['properties']['area'] = area
        return geojson


    def xy_to_latlon(self, prediction, bounding_box):
        """
            Convert prediction masks into list of geojsons

        Args:
            prediction (list): list of masks for ships
            bounding_box (list): list of boundingboxes for tile location

        Returns:
            list: list of geojsons for a given list of inferences
        """
        transform = rasterio.transform.from_bounds(
            *bounding_box, IMG_SIZE, IMG_SIZE
        )
        polygon_coordinates = list()

        for idx, ship in enumerate(regionprops(prediction.astype('uint8'))):
            bbox = ship.bbox
            xs = bbox[::2]
            ys = bbox[1::2]
            area = abs(xs[0] - xs[1]) * abs(ys[0] - ys[1])
            lons, lats = rasterio.transform.xy(
                transform, xs, ys
            )
            reformated_bbox = self.planet_downloader.prepare_coordinates(
                [lons[0], lats[0], lons[1], lats[1]]
            )
            polygon_coordinates.append(
                self.prepare_geojson(reformated_bbox, area)
            )
        return polygon_coordinates
