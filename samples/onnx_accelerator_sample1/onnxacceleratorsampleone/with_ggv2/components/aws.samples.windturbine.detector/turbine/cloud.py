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
import time
import os
import awsiot.greengrasscoreipc
import awsiot.greengrasscoreipc.model as model

class CloudConnector(object):
    def __init__(self):

        self.ipc_client = awsiot.greengrasscoreipc.connect()

    def publish_logs(self, data):
        dictionary = {
            "type": "rawdata",
            "data": data
        }
        op = self.ipc_client.new_publish_to_iot_core()
        op.activate(model.PublishToIoTCoreRequest(
            #https://docs.aws.amazon.com/greengrass/v2/developerguide/component-environment-variables.html
            topic_name="device/{}/logs".format(os.environ["AWS_IOT_THING_NAME"]),
            qos=model.QOS.AT_LEAST_ONCE,
            payload=json.dumps(dictionary).encode(),
        ))
        try:
            result = op.get_response().result(timeout=5.0)
            print("successfully published message:", result)
        except Exception as e:
            print("failed to publish message:", e)

    def publish_inference(self, anomalies, values, model_name, model_version, ts):
        dictionary = {
            "type": "inference",
            "model_name": model_name,
            "model_version": model_version,
            "anomalies": anomalies.tolist(),
            "values": values.tolist(),
            "ts": ts
        }
        op = self.ipc_client.new_publish_to_iot_core()
        op.activate(model.PublishToIoTCoreRequest(
            topic_name="device/{}/logs".format(os.environ["AWS_IOT_THING_NAME"]),
            qos=model.QOS.AT_LEAST_ONCE,
            payload=json.dumps(dictionary).encode(),
        ))
        try:
            result = op.get_response().result(timeout=5.0)
            print("successfully published message:", result)
        except Exception as e:
            print("failed to publish message:", e)      
