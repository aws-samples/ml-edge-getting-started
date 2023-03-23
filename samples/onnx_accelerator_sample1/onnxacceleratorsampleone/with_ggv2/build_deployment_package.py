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
import yaml

# first we need to retrieve the model pth file, for that let's consult the model package
model_package_arn = os.environ["MODEL_PACKAGE_ARN"]
deployment_bucket_name = os.environ['DEPLOYMENT_BUCKET_NAME']
region = os.environ["AWS_REGION"]

client_sm = boto3.client("sagemaker")

def update_component_config_in_json_file(filepath, version, component_name):
    with open(filepath+'gdk-config.json') as f:
        data = json.load(f)

        data['component'][component_name]['publish']['bucket'] = data['component'][component_name]['publish']['bucket'].replace('_BUCKET_NAME_', deployment_bucket_name)
        data['component'][component_name]['publish']['region'] = data['component'][component_name]['publish']['region'].replace('_REGION_', region)
        data['component'][component_name]['version'] = data['component'][component_name]['version'].replace('_COMPONENT_VERSION_', version)

        with open(filepath+'gdk-config.json', 'w') as f:
            json.dump(data, f)

def update_component_recipe_yaml_file(filepath, version, component_name, model_name):
    with open(filepath+"recipe.yaml", 'r') as stream:
        try:
            loaded = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Modify the fields from the dict
    if "detector" in filepath:
        loaded['ComponentConfiguration']['DefaultConfiguration']['model_name'] = model_name
        loaded['ComponentConfiguration']['DefaultConfiguration']['model_version'] = version
        
    loaded['ComponentName'] = component_name
    loaded['ComponentVersion'] = version
    loaded['ComponentPublisher'] = "Amazon.com"
    loaded['Manifests'][0]['Artifacts'][0]['URI'] = "s3://"+deployment_bucket_name+"/"+component_name+"/"+version+"/"+component_name+".zip"

    # Save it again
    with open(filepath+"recipe.yaml", 'w') as stream:
        try:
            yaml.dump(loaded, stream, default_flow_style=False)
        except yaml.YAMLError as exc:
            print(exc)

# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker.html#SageMaker.Client.describe_model_package
response = client_sm.describe_model_package(ModelPackageName=model_package_arn)

s3_model_location = response['InferenceSpecification']['Containers'][0]['ModelDataUrl']
model_package_version = response['ModelPackageVersion']

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

pytorch_model.eval() 
n_features=6
x = torch.rand(1,n_features,10,10).float()

input_names = [ "input"]
output_names = [ "output" ]

output_onnx_model_name = 'windturbine'
output_onnx_model = './aws.samples.windturbine.model/'+output_onnx_model_name+'.onnx'

torch.onnx.export(pytorch_model,
                 x,
                 output_onnx_model,
                 verbose=True,
                 input_names=input_names,
                 output_names=output_names,
                 export_params=True,
                 )

# Update the recipe/config for each component
component_version = '1.0.'+str(model_package_version)
update_component_config_in_json_file('./aws.samples.windturbine.model/', component_version, 'aws.samples.windturbine.model')
update_component_config_in_json_file('./aws.samples.windturbine.detector.venv/', component_version, 'aws.samples.windturbine.detector.venv')
update_component_config_in_json_file('./aws.samples.windturbine.detector/', component_version, 'aws.samples.windturbine.detector')

update_component_recipe_yaml_file('./aws.samples.windturbine.model/', component_version, 'aws.samples.windturbine.model', output_onnx_model_name)
update_component_recipe_yaml_file('./aws.samples.windturbine.detector/', component_version, 'aws.samples.windturbine.detector', output_onnx_model_name)


