import boto3
import json
import os

from infer import Infer

API_KEY = os.environ['API_KEY']

SQS_QUEUE = 'ship_detection_sqs'

# will need to change this to role based permission
SQS_CONNECTOR = boto3.resource(
    'sqs',
    region_name='us-east-1',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
)

detected_queue = SQS_CONNECTOR.get_queue_by_name(QueueName='ship_detected_sqs')
while True:
    # Get the queue
    queue = SQS_CONNECTOR.get_queue_by_name(QueueName=SQS_QUEUE)

    # extract date information for message
    for message in queue.receive_messages(MessageAttributeNames=['date']):
        message_body = message.body
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
        message.delete()
