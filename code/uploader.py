import os
import subprocess
import base64
import json
import rasterio
import requests

from glob import glob

from rasterio.io import MemoryFile
from rasterio.warp import reproject, calculate_default_transform, Resampling

from zipfile import ZipFile

BASE_URL = "https://labeler.nasa-impact.net"
DEFAULT_CRS = 'EPSG:4326'

LOGIN_URL = f"{BASE_URL}/accounts/login/"

FAKE_HEADERS = {
    'Host': 'labeler.nasa-impact.net',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'Origin': f'{BASE_URL}',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Referer': f'{BASE_URL}/accounts/login/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,hi-IN;q=0.8,hi;q=0.7',
}

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
        self.csrf_token = self.login(username, password)
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
                filename = filename_format.format(index)
                self.upload_one_shapefile(polygon, filename)


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
        filename = foldername + '/' + updated_filename
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


    def upload_one_shapefile(self, polygon, filename):
        """
        Upload one shapefile into imagelabeler

        Args:
            polygon (dict): Polygon in geojson form
            filename (str): filename to be uploaded into imagelabeler
        """
        geojson = { 'type': 'FeatureCollection', 'features': [polygon] }
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


    def login(self, username, password):
        """
        Logs in user and sets up headers pretending to be a browser

        Args:
            username: ImageLabeler username
            password: ImageLabeler password
        """
        self.client = requests.session()
        self.client.get(LOGIN_URL)
        self.headers = FAKE_HEADERS

        csrftoken = self.client.cookies['csrftoken']

        self.login_data = {
            'login': username,
            'password': password,
            'csrfmiddlewaretoken': csrftoken,
        }
        # Log into the server
        response = self.client.post(
            LOGIN_URL,
            data=self.login_data,
            headers=self.headers
        )
        print(f'Login status: {response.status_code}')
        # CSRF Token changes after login, get that
        csrftoken = self.client.cookies['csrftoken']

        # Update the login_data's csrftoken field
        self.login_data['csrfmiddlewaretoken'] = csrftoken

        # Change the referer header for uploads
        self.headers['Referer'] = IL_URL['geotiff']

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
            response = self.client.post(
                IL_URL[file_type],
                data=self.login_data,
                files=files, headers=file_headers
            )
            return response.text, response.status_code

    @classmethod
    def mkdir(cls, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)
            print(f'directory created: {dirname}')
