import os
import subprocess
import base64
import json
import rasterio
import requests

from glob import glob
from zipfile import ZipFile

BASE_URL = "https://labeler.nasa-impact.net"
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

class Uploader:
    def __init__(self, username, password):
        self.csrf_token = self.login(username, password)
        Uploader.mkdir('updated')

    def upload_detections(self, detections):
        date = detections['date'].replace('-', '')
        for detection in detections['detections']:
            location_name = detection['location'].replace(' ', '')
            polygons = detection['geojson']['features']
            filename_format = f"{location_name}_{date}T000000_{{}}"
            for index, polygon in enumerate(polygons):
                self.upload_one_shapefile(index, polygon, filename_format)

    def upload_geotiffs(self, file_name):
        foldername = f"updated/{file_name.split('/')[-1].split('.')[0]}"
        Uploader.mkdir(foldername)

        with ZipFile(file_name) as zip_file:
            file_names = zip_file.namelist()
            for compressed_file in compressed_files:
                compressed_file = str(compressed_file)
                _, extension = os.path.splitext(compressed_file)
                if extension == '.tif':
                    split = compressed_file.split('/')[-1].split('_')
                    date_time = f"{'T'.join(split[0:2])}_{'_'.join(split[2:])}"
                    filename = foldername + '/' + date_time
                    mem_tiff = zip_file.read(compressed_file)
                    tiff_file = MemoryFile(mem_tiff).open()
                    updated_profile = self.calculate_updated_profile(tiff_file)
                    with rasterio.open(filename, 'w', **profile) as dst:
                        for band in range(1, 4):
                            reproject(source=rasterio.band(tiff_file, band),
                                destination=rasterio.band(dst, band),
                                src_transform=tiff_file.transform,
                                src_crs=tiff_file.crs,
                                dst_transform=transform,
                                dst_crs='EPSG:4326',
                                resampling=Resampling.nearest)


    def calculate_updated_profile(self, tiff_file):
        profile = tiff_file.profile
        transform, width, height = calculate_default_transform(
            tiff_file.crs,
            'EPSG:4326',
            tiff_file.width,
            tiff_file.height,
            *tiff_file.bounds
        )
        profile.update(
            crs='EPSG:4326',
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
        self.upload_to_image_labeler(f"{filename}.zip")
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
        self.headers['Referer'] = f'{BASE_URL}/geotiff/'


    def upload_to_image_labeler(self, file_name):
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
                SHAPEFILE_URL,
                data=self.login_data,
                files=files, headers=file_headers
            )
            return response.text, response.status_code

    @classmethod
    def mkdir(cls, dirname):
        if not os.path.exists(dirname):
            os.mkdir(dirname)
            print(f'directory created: {dirname}')
