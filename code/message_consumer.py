import boto3
import json
import os
import time

from infer import Infer

API_KEY = os.environ['API_KEY']

SQS_QUEUE = 'ship_detection_sqs'
ROLE_NAME = 'ShipDetectionEcsRole'

# Will need to make account number a variable too.
ROLE_ARN = os.getenv('ROLE_ARN') or f"arn:aws:iam::853558080719:role/{ROLE_NAME}"


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
    sqs_connector = session.resource('sqs')
    detection_queue = sqs_connector.get_queue_by_name(
        QueueName=SQS_QUEUE
    )
    detected_queue = sqs_connector.get_queue_by_name(
        QueueName='ship_detected_sqs'
    )
    print('Poll Started')
    # extract date information for message
    for msg in detection_queue.receive_messages(MessageAttributeNames=['date']):
        message_body = msg.body
        if message_body is not None:
            date = json.loads(message_body).get('date')
            infer = Infer(date, credential=API_KEY)
            detections = infer.infer()
            detections = { 'date': date, 'detections': detections }
            print(f"for {date}, number of detections: {len(detections['detections'])}")
            detected_queue.send_message(MessageBody=json.dumps(detections))
        else:
            print('Please specify date')
        # delete message from queue
        msg.delete()
    print('Poll completed')
    # sleep for 10 second before trying to check new messages
    time.sleep(10)