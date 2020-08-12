import json

import mercantile

import numpy as np

import requests

from config import ZOOM_LEVEL


BODY = {
    "filter": {
        "type": "AndFilter",
        "config": [
            {
                "type": "GeometryFilter",
                "field_name": "geometry",
                "config": {
                    "type": "Polygon",
                    "coordinates": []
                }
            },
            {
                "type": "DateRangeFilter",
                "field_name": "acquired",
                "config": {
                        "gt": "",
                        "lte": ""
                }
            },
            {
                "type": "RangeFilter",
                "field_name": "cloud_cover",
                "config": {
                    "lte": 0.5
                }
            }
        ]
    },
    "item_types": ["PSScene3Band"]
}

SEARCH_URL = 'https://api.planet.com/data/v1/quick-search'


class PlanetDownloader:

    def __init__(self, api_key):
        """
            Initializer

        Args:
            api_key (str): api key for planet data access
        """
        self.api_key = api_key

    def search_ids(self, extent, start_date_time, end_date_time):
        """
            Search scene ids in planet

        Args:
            extent (list): list of coordinates
            start_date_time (str): start time in the format "yyyymmddThhddssZ"
            end_date_time (str): end time in the format "yyyymmddThhddssZ"

        Returns:
            list: list of ids and tile sizes
        """
        body = BODY
        body['filter']['config'][0]['config']['coordinates'] = \
            self.prepare_coordinates(extent)
        body['filter']['config'][1]['config'] = {
            'gt': start_date_time,
            'lte': end_date_time
        }
        response = requests.post(
            SEARCH_URL, auth=(self.api_key, ''), json=body
        )
        # if not 200 raise error
        response.raise_for_status()
        parsed_content = json.loads(response.text)

        return self.extract_data(parsed_content['features'])

    def extract_data(self, parsed_data):
        """
            Extract coordinates and tile information from the response

        Args:
            parsed_data (list): list of items returned by planet

        Returns:
            list: list of item ids and x, y tiles.
        """
        extracted_data = []
        for feature in parsed_data:
            current_data = {'images': []}
            current_data['id'] = feature['id']
            reverted_coordinates = self.revert_coordinates(
                feature['geometry']['coordinates']
            )
            current_data['coordinates'] = reverted_coordinates
            current_data['tiles'] = self.tile_indices(reverted_coordinates)
            extracted_data.append(current_data)
        return extracted_data

    def revert_coordinates(self, coordinates):
        """
            Revert the coordinates from an extended notation to flat coordinate
            notation

        Args:
            coordinates (list): list: [
                [left, down],
                [right, down],
                [right, up],
                [left, up],
                [left, down]
            ]

        Returns:
            list: [left, down, right, top]
        """
        coordinates = np.asarray(coordinates)
        lats = coordinates[:, :, 1]
        lons = coordinates[:, :, 0]
        return [lons.min(), lats.min(), lons.max(), lats.max()]

    def tile_indices(self, coordinates):
        """
            Extract tile indices based on coordinates

        Args:
            coordinates (list): [left, down, right, top]

        Returns:
            list: [[start_x, end_x], [start_y, end_y]]
        """
        start_x, start_y, _ = mercantile.tile(
            coordinates[0],
            coordinates[3],
            ZOOM_LEVEL
        )
        end_x, end_y, _ = mercantile.tile(
            coordinates[2],
            coordinates[1],
            ZOOM_LEVEL
        )
        return [[start_x, end_x], [start_y, end_y]]

    def prepare_coordinates(self, extent):
        """
            Revert the coordinates from flat notation to extended coordinate
            notation

        Args:
            extent (list): [left, down, right, up]

        Returns:
            list: [
                [left, down],
                [right, down],
                [right, up],
                [left, up],
                [left, down]
            ]
        """
        return [
            [
                [extent[0], extent[1]],
                [extent[2], extent[1]],
                [extent[2], extent[3]],
                [extent[0], extent[3]],
                [extent[0], extent[1]]
            ]
        ]
