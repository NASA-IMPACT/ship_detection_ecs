import base64
import json
import os
import rasterio
import requests
import subprocess

from glob import glob
from rasterio.io import MemoryFile
from rasterio.warp import reproject, calculate_default_transform, Resampling
from zipfile import ZipFile

BASE_URL = "https://labeler.nasa-impact.net"

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

DEFAULT_CRS = 'EPSG:4326'

LOGIN_URL = f"{BASE_URL}/accounts/login/"

OGR_OGR = ['ogr2ogr', '-f', 'ESRI Shapefile']

SHAPEFILE_URL = f"{BASE_URL}/api/shapefiles"

IL_URL = {
    'shapefile': f"{BASE_URL}/api/shapefiles",
    'geotiff': f"{BASE_URL}/api/geotiffs"
}


class Uploader:

    def __init__(self, username, password):
        """
        Initializer

        Args:
            username (str): ImageLabeler Username
            password (str): ImageLabeler Password
        """
        self.request_token(username, password)
        Uploader.mkdir('updated')


    def upload_detections(self, detections):
        """
        Upload shapes to imagelabeler

        Args:
            detections (dict): Dict of detections
            EG: {
                    'date': '2020-01-01',
                    'detections': [{
                        'location': 'New York',
                        'geojson': {...},
                        'scene_ids': [...],
                    }]
                }
        """
        date = detections['date'].replace('-', '')
        for detection in detections['detections']:
            location_name = detection['location'].replace(' ', '')
            polygons = detection['geojson']['features']
            filename_format = f"{location_name}_{date}T000000_{{}}"
            for index, polygon in enumerate(polygons):
                self.upload_one_shapefile(index, polygon, filename_format)

    def upload_geotiffs(self, file_name):
        """
        Upload geotiffs into imagelabeler

        Args:
            file_name (str): path to downloaded geotiff.
        """
        foldername, _ = os.path.splitext(file_name)
        Uploader.mkdir(foldername)
        location = ''.join(foldername.split('/')[-1].split('_')[: 2])

        with ZipFile(file_name) as zip_file:
            compressed_files = zip_file.namelist()
            for compressed_file in compressed_files:
                compressed_file = str(compressed_file)
                _, extension = os.path.splitext(compressed_file)
                if extension == '.tif':
                    self.process_geotiff(
                        compressed_file,
                        location,
                        zip_file,
                        foldername
                    )


    def process_geotiff(self, compressed_file, location, zip_file, foldername):
        """
        Reproject and upload geotiff into imagelabeler

        Args:
            compressed_file (str): path of tif file in zip file
            location (str): location of detection
            zip_file (zipfile.ZipFile): zipfile instance
            foldername (str): foldername of where to store file
        """
        split = compressed_file.split('/')[-1].split('_')
        updated_filename = f"{location}_{'T'.join(split[0:2])}_{'_'.join(split[2:])}"
        filename = f"{foldername}/{updated_filename}"
        mem_tiff = zip_file.read(compressed_file)
        tiff_file = MemoryFile(mem_tiff).open()
        updated_profile = self.calculate_updated_profile(tiff_file)
        with rasterio.open(filename, 'w', **updated_profile) as dst:
            for band in range(1, 4):
                reproject(
                    source=rasterio.band(tiff_file, band),
                    destination=rasterio.band(dst, band),
                    src_transform=tiff_file.transform,
                    src_crs=tiff_file.crs,
                    dst_transform=updated_profile['transform'],
                    dst_crs=DEFAULT_CRS,
                    resampling=Resampling.nearest)
        _, status_code = self.upload_to_image_labeler(filename)
        if status_code == 200:
            os.remove(filename)
        print(f"{filename} uploaded to imagelabeler with: {status_code}")


    def calculate_updated_profile(self, tiff_file):
        """
        Create updated profile for the provided tiff_file

        Args:
            tiff_file (rasterio.io.MemoryFile): rasterio memoryfile.

        Returns:
            dict: updated profile for new tiff file
        """
        profile = tiff_file.profile
        transform, width, height = calculate_default_transform(
            tiff_file.crs,
            DEFAULT_CRS,
            tiff_file.width,
            tiff_file.height,
            *tiff_file.bounds
        )
        profile.update(
            crs=DEFAULT_CRS,
            transform=transform,
            width=width,
            height=height,
            count=3,
            nodata=0,
            compress='lzw',
            dtype='uint8'
        )
        return profile


    def upload_one_shapefile(self, index, polygon, filename_format):
        geojson = { 'type': 'FeatureCollection', 'features': [polygon] }
        filename = filename_format.format(index)
        geojson_file_name = f"{filename}.geojson"
        with open(geojson_file_name, 'w') as geojson_file:
            json.dump(geojson, geojson_file)
        shp_file_name = f"{filename}.shp"
        args = OGR_OGR + [shp_file_name, geojson_file_name]
        subprocess.Popen(args).wait()
        os.remove(geojson_file_name)
        with ZipFile(f"{filename}.zip", 'w') as zip_file:
            for shp_file in glob(f"{filename}.*"):
                zip_file.write(shp_file)
        self.upload_to_image_labeler(f"{filename}.zip", file_type='shapefile')
        # remove files after uploading
        for local_file in glob(f"{filename}*"):
            os.remove(local_file)


    def request_token(self, username, password):
        """
        this funtion will return an authentication token for users to use
        Args:
            username (string) : registered username of the user using the script
            password (string) : password associated with the user
        Exceptions:
            UserNotFound: Given user does not exist
        Returns:
            headers (dict): {
                "Authorization": "Bearer ..."
            }
        """

        payload = {
            "username": username,
            "password": password,
            "grant_type": "password"
        }

        response = requests.post(
            f"{BASE_URL}/authentication/token/",
            data=payload,
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        access_token = json.loads(response.text)['access_token']
        self.headers = {
            'Authorization': f"Bearer {access_token}",
        }


    def upload_to_image_labeler(self, file_name, file_type='geotiff'):
        """
        Uploads a single shapefile to the image labeler

        Args:
            file_name : name of zip file containing shapefiles

        Returns:
            response (tuple[string]): response text, response code
        """
        with open(file_name, 'rb') as upload_file_name:
            file_headers = {
                **self.headers,
            }
            files = {
                'file': (file_name, upload_file_name),
            }
            response = requests.post(
                IL_URL[file_type],
                files=files,
                headers=file_headers
            )
            return response.text, response.status_code

    @classmethod
    def mkdir(cls, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)
            print(f'directory created: {dirname}')
