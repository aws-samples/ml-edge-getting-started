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
import uuid
import os
import urllib.parse

iot_job_client = boto3.client('iot')
thing_group_name = os.environ['THING_GROUP_NAME']
iot_provisioning_role= os.environ['ARN_IOT_PROVISIONING_ROLE']

def handler(event, context):
    # grab information about the new deployment package ready for use
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    job_document_source = 'https://s3.amazonaws.com/'+bucket_name+'/'+key

    print("Job document is located at: " + job_document_source)

    # submit the iot job
    job_id = str(uuid.uuid1())
    thing_group_arn = iot_job_client.describe_thing_group(thingGroupName=thing_group_name)['thingGroupArn']
    print(thing_group_arn)
    try:
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iot.html#IoT.Client.create_job
        iot_job_client.create_job(
            jobId=job_id,
            targets=[thing_group_arn], # the target of the iot job is the entire thing group
            documentSource=job_document_source,
            timeoutConfig={'inProgressTimeoutInMinutes': 10},
            presignedUrlConfig={ # this presigned url will be used by iot to download the document and execute the job
                'roleArn': iot_provisioning_role,
                'expiresInSec': 3600
            },
        )
    except Exception as e:
        print(e)
        raise e