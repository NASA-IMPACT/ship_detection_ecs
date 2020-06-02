import boto3
import json
import os
import time

from infer import Infer

ACCOUNT_NUMBER = '853558080719'
API_KEY = os.environ['API_KEY']
DETECTED_QUEUE = 'ship_detected_sqs'
QUEUE_URL = f"https://queue.amazonaws.com/{ACCOUNT_NUMBER}/{{}}"
ROLE_ARN = f'arn:aws:iam::{ACCOUNT_NUMBER}:role/{ROLE_NAME}'
ROLE_NAME = 'ShipDetectionEcsRole'

ROLE_ARN = f"arn:aws:iam::{ACCOUNT_NUMBER}:role/{ROLE_NAME}"
SQS_QUEUE = 'ship_detection_sqs'

def assumed_role_session():
    client = boto3.client('sts')
    creds = client.assume_role(
        RoleArn=ROLE_ARN, RoleSessionName=ROLE_NAME
    )['Credentials']
    return boto3.session.Session(
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )


while True:
    # Get the queue
    session = assumed_role_session()
    sqs_connector = session.client('sqs')
    detection_queue_url = QUEUE_URL.format(SQS_QUEUE)
    detected_queue_url = QUEUE_URL.format(DETECTED_QUEUE)

    # extract date information for message
    for msg in sqs_connector.receive_messages(
        QueueUrl=detection_queue_url, MessageAttributeNames=['date']
    ):
        message_body = msg.body
        if message_body is not None:
            date = json.loads(message_body).get('date')
            infer = Infer(date, credential=API_KEY)
            detections = infer.infer()
            detections = { 'date': date, 'detections': detections }
            print(f"for {date}, number of detections: {len(detections['detections'])}")
            sqs_connector.send_message(
                QueueUrl=detected_queue_url,
                MessageBody=json.dumps(detections)
            )
        else:
            print('Please specify date')
        # delete message from queue
        msg.delete()
    print('Poll completed')
    # sleep for 10 second before trying to check new messages
    time.sleep(10)