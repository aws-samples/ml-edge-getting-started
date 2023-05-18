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

deployment_bucket = os.environ['DEPLOYMENT_BUCKET']

s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))

def get_latest_model():
    get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))

    list_models = s3_client.list_objects_v2(Bucket=deployment_bucket)['Contents']
    last_added_model = [obj['Key'] for obj in sorted(list_models, key=get_last_modified)][0]

    print(last_added_model)

    return last_added_model

def create_presigned_get(bucket_name, object_name):
    params = {
            'Bucket': bucket_name,
            'Key': object_name
          }

    try:
        response = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            HttpMethod='GET',
            Params=params,
            ExpiresIn=120
        )
    except ClientError as e:
        print(e)
        return None

    return response

def handler(event, context):
    print(event)
    print(context)

    latest_model = get_latest_model()
    result = create_presigned_get(deployment_bucket, latest_model)
    
    # the model is built as follow: codebuildid/onnxpackagebuilder/model_version.onnx
    model_info = latest_model.split('/')[2]

    model_name = os.path.splitext(model_info)
    model, model_version = model_name[0].rsplit("_", 1)
    
    dictionary = {
        'download_url': result,
        'filename': model_info,
        'model_name': model,
        'model_version': model_version
    }
    
    print(json.dumps(dictionary, indent = 4))

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8'
        },
        'body': json.dumps(dictionary)
    }
    