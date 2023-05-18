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
import onnxruntime
import onnx
import numpy as np

# first we need to retrieve the model pth file, for that let's consult the model package
model_package_arn = os.environ["MODEL_PACKAGE_ARN"]
deployment_bucket_name = os.environ['DEPLOYMENT_BUCKET_NAME']
region = os.environ["AWS_REGION"]

client_sm = boto3.client("sagemaker")

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

pytorch_model.eval() 
x = torch.rand(1, 3, 224, 224, requires_grad=True)

torch_out = pytorch_model(x)

input_names = [ "input"]
output_names = [ "output" ]

output_onnx_model_name = 'imageclassification_'+str(model_package_version)+'.onnx'

# export it to onnx format
torch.onnx.export(pytorch_model,
                 x,
                 output_onnx_model_name,
                 verbose=True,
                 input_names=input_names,
                 output_names=output_names,
                 export_params=True,
                 )

# verify the model
onnx_model = onnx.load(output_onnx_model_name)
onnx.checker.check_model(onnx_model)

ort_session = onnxruntime.InferenceSession(output_onnx_model_name)

def to_numpy(tensor):
    return tensor.detach().cpu().numpy() if tensor.requires_grad else tensor.cpu().numpy()

ort_inputs = {ort_session.get_inputs()[0].name: to_numpy(x)}
ort_outs = ort_session.run(None, ort_inputs)

np.testing.assert_allclose(to_numpy(torch_out), ort_outs[0], rtol=1e-03, atol=1e-05)

print("Valid model")