# from infer import Infer
# import os
# import time

# start_time = time.time()
# i = Infer(credential=os.environ['API_KEY'])
# print(i.infer('2020-03-03'))
# end_time = time.time()

# print('total_time:', end_time - start_time)

from uploader import Uploader

uploader = Uploader('admin', '4ubzRCR5ANwcBy2')

print(uploader.upload(
  {
    'date': '2020-03-27',
    'detections': [
      {
        'location': 'Los Angeles',
        'geojson': {
          "type":"FeatureCollection", "features": [
            {"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[-118.118649,33.688918],[-118.114872,33.688918],[-118.114872,33.690561],[-118.118649,33.690561],[-118.118649,33.688918]]]},"properties":{},"id":0}
]}}]}))
