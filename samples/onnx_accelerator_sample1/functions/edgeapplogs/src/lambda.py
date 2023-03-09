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
import urllib.request
import os
import io
import boto3
import time

log_group_name = os.environ['LOG_GROUP_NAME']
log_stream_raw_data_name = os.environ['LOG_STREAM_RAW_DATA_NAME']
log_stream_inference_name = os.environ['LOG_STREAM_INFERENCE_NAME']


logs_client = boto3.client('logs')

def put_events(log_stream_name, data):
    logs_client.put_log_events(logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[data])

def handler(event, context):
    device_name = event['clientid']

    if event['type'] == 'rawdata':
        data = event['data']['values']
        item = {
            "timestamp": round(time.time() * 1000),
            "message": ' '.join([event['data']['ts'], device_name] + [str(i) for i in data])
        }
        put_events(log_stream_raw_data_name, item)

    elif event['type'] == 'inference':
        data = event['values']
        item = {
            "timestamp": round(time.time() * 1000),
            "message": ' '.join([event['ts'], device_name, event['model_name'], event['model_version']] + [str(i) for i in event["anomalies"]] + [str(i) for i in data])
        }
        put_events(log_stream_inference_name, item)
    else:
        raise Exception("Invalid event: %s" % json.dumps(event))