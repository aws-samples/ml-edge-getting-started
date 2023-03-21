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

import torch
import tarfile
import boto3
import os
import json
import pathlib
import shutil

# first we need to retrieve the model pth file, for that let's consult the model package
model_package_arn = os.environ["MODEL_PACKAGE_ARN"]
project_config = os.environ["CODEBUILD_BUILD_ID"].split(':') # build_id is built as follow: "project name:build number"
codebuild_project_name = project_config[0]
build_id = project_config[1]
deployment_bucket_name = os.environ['DEPLOYMENT_BUCKET_NAME']
region = os.environ["AWS_REGION"]

client_sm = boto3.client("sagemaker")
client_greengrass = boto3.client('greengrassv2')
s3Resource = boto3.resource('s3')

# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker.html#SageMaker.Client.describe_model_package
response = client_sm.describe_model_package(ModelPackageName=model_package_arn)

s3_model_location = response['InferenceSpecification']['Containers'][0]['ModelDataUrl']
model_package_version = response['ModelPackageVersion']

print(s3_model_location)

# let's pull the compressed model data from the bucket
client_s3 = boto3.client("s3")

bucket, key = s3_model_location.split('/',2)[-1].split('/',1)

try:
    client_s3.download_file(bucket, key, 'model.tar.gz')
except Exception as e:
    print(e)

# let's unzip the model package
file = tarfile.open('model.tar.gz')
file.extractall('.')
file.close()

# now load the model
pytorch_model = torch.load('model.pth',  map_location='cpu')

print(torch.__version__)

pytorch_model.eval() 
n_features=6
x = torch.rand(1,n_features,10,10).float()

input_names = [ "input"]
output_names = [ "output" ]

output_onnx_model_name = 'windturbine'
output_onnx_model = './com.aws.onnxedgeapp/'+output_onnx_model_name+'.onnx'

torch.onnx.export(pytorch_model,
                 x,
                 output_onnx_model,
                 verbose=True,
                 input_names=input_names,
                 output_names=output_names,
                 export_params=True,
                 )

# Creating the ZIP file of the component artifact
component_zip_output = './component.zip'

shutil.make_archive('component', 'zip', 'com.aws.onnxedgeapp')

if os.path.exists(component_zip_output):
   print("Component zip file created") 
else: 
   print("Component zip file not created")
   exit()

# before we create the component, we need to upload its artifacts to the s3 bucket
try: 
    s3Resource.meta.client.upload_file('./component.zip', deployment_bucket_name, build_id+"/"+codebuild_project_name+"/component.zip")
except Exception as err:
    print(err)
    exit()

# now let's build the component recipe 
dictionary = {
    "RecipeFormatVersion": "2020-01-25",
    "ComponentName": "com.aws.onnxedgeapp",
    "ComponentVersion": "1.0."+str(model_package_version),
    "ComponentDescription": "Windturbine Inference Component",
    "ComponentPublisher": "AWS Samples",
    "ComponentConfiguration": {
        "DefaultConfiguration": {
        "Configuration": {
            "model_name": output_onnx_model_name,
            "model_version": str(model_package_version),
            "broker": "localhost",
            "port": 1883,
            "client_id": "edge_application"
        },
        "accessControl": {
            "aws.greengrass.ipc.mqttproxy": {
            "policy_1": {
                "operations": [
                "aws.greengrass#PublishToIoTCore"
                ],
                "resources": [
                "*"
                ]
            }
            }
        }
        }
    },
    "Manifests": [
        {
            "Platform": {
                "os": "linux",
                "architecture": "aarch64"
            },
            "Artifacts": [
                {
                "URI": "s3://"+deployment_bucket_name+"/"+build_id+"/"+codebuild_project_name+"/component.zip",
                "Unarchive": "ZIP",
                "Permission":{
                    "Execute": "OWNER"
                }
                }
            ],
            "Lifecycle": {
                "Install": {
                "Script": "python3 -m pip install -r {artifacts:decompressedPath}/component/requirements.txt",
                "RequiresPrivilege": "true"
                },
                "Run": {
                "Script": "python3 -u {artifacts:decompressedPath}/component/edge_application.py --config '''{configuration:/Configuration}'''",
                "Setenv": {
                "ONNX_MODEL_PATH": "{artifacts:decompressedPath}/component/"+output_onnx_model_name+".onnx",
                "STATISTICS_PATH": "{artifacts:decompressedPath}/component/statistics/"
                },
                "RequiresPrivilege": "true",
                "Timeout": 1200
                },
                "Shutdown": {
                "Script": "echo \"INFERENCE CODE SHUTTING DOWN\"",
                "RequiresPrivilege": "true"
                }
            }
        }
    ]
}
 
# Serializing json
json_object = json.dumps(dictionary, indent=4)

# now let's build the greengrass component
# this can fail if the specific version of the component already exists
# the component with the same version needs to be removed
response = client_greengrass.create_component_version(
   inlineRecipe=json_object
)


