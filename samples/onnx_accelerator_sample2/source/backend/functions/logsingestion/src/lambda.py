# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import os
import boto3
import time

logs_client = boto3.client('logs')

log_group_name = os.environ['LOG_GROUP_NAME']
log_stream_inference_name = os.environ['LOG_STREAM_INFERENCE_NAME']    

def handler(event, context):

    print(event)

    data = json.loads(event['body'])
    username = event['requestContext']['authorizer']['jwt']['claims']['cognito:username']

    item = {
            "timestamp": round(time.time() * 1000),
            "message": ' '.join([data['ts'], username, data['modelName'], data['label'], str(data['score']), data['inputImageUrl'], data['inputImageKey']])
        }

    logs_client.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_inference_name,
        logEvents=[item]
    )
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        'body': json.dumps('Logs ingested!')
    }