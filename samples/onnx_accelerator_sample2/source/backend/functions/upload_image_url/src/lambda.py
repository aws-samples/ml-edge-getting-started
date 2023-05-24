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
import boto3
import os
import hashlib
import time
from botocore.exceptions import ClientError

deployment_bucket = os.environ['INPUT_IMAGES_BUCKET']

def create_presigned_post(bucket_name, object_name, fields=None, conditions=None):
    s3_client = boto3.client('s3')

    try:
        response = s3_client.generate_presigned_post(
            bucket_name,
            object_name,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=60
        )
    except ClientError as e:
        print(e)
        return None

    return response

def handler(event, context):
    print(event)
    print(context)
    uniquehash = hashlib.sha1("{}".format(time.time_ns()).encode('utf-8')).hexdigest()
    result = create_presigned_post(deployment_bucket, "new/{}/{}.jpg".format(uniquehash[:2],uniquehash))

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        'body': json.dumps(result)
    }

