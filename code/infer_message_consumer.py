import boto3
import json
import os
import time

from config import ACCOUNT_NUMBER
from infer import Infer
from uploader import Uploader

API_KEY = os.environ['API_KEY']

DETECTED_QUEUE = 'ship_detected_sqs'

IL_USER_NAME = os.environ['IL_USER_NAME']
IL_PASSWORD = os.environ['IL_PASSWORD']

PLANET_ORDER_QUEUE = 'planet_order_place_sqs'
QUEUE_URL = f"https://queue.amazonaws.com/{ACCOUNT_NUMBER}/{{}}"

ROLE_NAME = 'PlanetOrderEc2Role'
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_NUMBER}:role/{ROLE_NAME}'

SQS_QUEUE = 'ship_detection_sqs'


def assumed_role_session():
    client = boto3.client('sts')
    creds = client.assume_role(
        RoleArn=ROLE_ARN, RoleSessionName=ROLE_NAME
    )['Credentials']
    return boto3.session.Session(
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken'],
        region_name='us-east-1'
    )

infer = Infer(credential=API_KEY)
uploader = Uploader(IL_USER_NAME, IL_PASSWORD)
while True:
    # Get the queue
    session = assumed_role_session()
    sqs_connector = session.client('sqs')
    detection_queue_url = QUEUE_URL.format(SQS_QUEUE)
    planet_order_queue_url = QUEUE_URL.format(PLANET_ORDER_QUEUE)
    detection_messages = sqs_connector.receive_message(
        QueueUrl=detection_queue_url, MessageAttributeNames=['date']
    )
    messages = detection_messages.get('Messages', [])
    # extract date information for message
    for msg in messages:
        message_body = msg['Body'] or '{}'
        message = json.loads(message_body)
        date = message.get('date')
        extents = message.get('extents')
        if date:
            location_wise_detections, detection_count = infer.infer(
                date,
                extents=extents
            )
            print(f"{date}: number of detections: {detection_count}")
            detections = {
                'date': date,
                'detections': location_wise_detections
            }
            uploader.upload_detections(detections)
            sqs_connector.send_message(
                QueueUrl=planet_order_queue_url,
                MessageBody=json.dumps(detections)
            )
            # Segregating this for now.
            # sqs_connector.send_message(
            #     QueueUrl=detected_queue_url,
            #     MessageBody=json.dumps(detections)
            # )
        else:
            print('Please specify date')
        # delete message from queue
        session = assumed_role_session()
        sqs_connector = session.client('sqs')
        sqs_connector.delete_message(
            QueueUrl=detection_queue_url,
            ReceiptHandle=msg['ReceiptHandle']
        )
    print('Poll completed')
    # sleep for 10 second before trying to check new messages
    time.sleep(10)
