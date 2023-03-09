#!/usr/bin/python3
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
import os
from aws_cdk import App, Environment, Aspects
from onnxacceleratorsampleone.main_stack import MainStack
import boto3

#from cdk_nag import AwsSolutionsChecks

sts_client = boto3.client("sts")

# for development, use account/region from cdk cli
dev_env = Environment(
  account=os.environ.get('CDK_DEFAULT_ACCOUNT', sts_client.get_caller_identity()["Account"]),
  region=os.getenv('CDK_DEFAULT_REGION')
)

app = App()
# Add cdk-nag aws solutions pack (with verbose logging)
#Aspects.of(app).add(AwsSolutionsChecks(verbose= False))

mainStack = MainStack(app, 
  "onnxacceleratorsampleone-dev", 
  env=dev_env,
  description='(uksb-1tupboclu) Stack for onnx model export and deployment at the edge')

# MyStack(app, "onnxacceleratorsampleone-prod", env=prod_env)

app.synth()