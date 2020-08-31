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

QUEUE_URL = f"https://queue.amazonaws.com/{ACCOUNT_NUMBER}/{{}}"

ROLE_NAME = 'PlanetOrderEc2Role'
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_NUMBER}:role/{ROLE_NAME}'

SQS_QUEUE = 'planet_order_received_sqs'


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

uploader = Uploader(IL_USER_NAME, IL_PASSWORD)
Uploader.mkdir('updated')

while True:
    # Get the queue
    session = assumed_role_session()
    sqs_connector = session.client('sqs')
    order_queue_url = QUEUE_URL.format(SQS_QUEUE)
    order_messages = sqs_connector.receive_message(
        QueueUrl=order_queue_url, MessageAttributeNames=['date']
    )
    messages = order_messages.get('Messages', [])
    s3 = session.resource('s3')
    # extract date information for message
    for msg in messages:
        message_body = msg['Body'] or '{}'
        message = json.loads(message_body)
        records = message.get('Records', [])
        for record in records:
            s3_details = record.get('s3')
            bucket_name = s3_details.get('bucket').get('name')
            added_object = s3_details.get('object').get('key')
            _, ext = os.path.splitext(added_object)
            if ext == '.zip':
                download_filename = f"updated/{added_object.split('/')[-1]}"
                s3.Bucket(bucket_name).download_file(
                    added_object,
                    download_filename
                )
                uploader.upload_geotiffs(download_filename)
                os.remove(download_filename)
        session = assumed_role_session()
        sqs_connector = session.client('sqs')
        sqs_connector.delete_message(
            QueueUrl=order_queue_url,
            ReceiptHandle=msg['ReceiptHandle']
        )
    print('Poll completed')
    # sleep for 10 second before trying to check new messages
    time.sleep(10)
