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

#https://projen.io/api/API.html#class-awscdkpythonapp--
from projen.awscdk import AwsCdkPythonApp

project = AwsCdkPythonApp(
    author_name="Amazon Web Services",
    cdk_version="2.1.0",
    module_name="onnxacceleratorsampleone",
    name="onnxacceleratorsampleone",
    version="0.1.0",
    context={"thing_name":"WindTurbine", "thing_group_name":"WindTurbines", "devices_logs_topic":"device/+/logs"}
)

project.add_dependency('boto3@1.26.72')
project.add_dependency('cdk-nag@2.22.28')

project.add_git_ignore(".DS_Store")
project.add_git_ignore("edge_application/certs")
project.add_git_ignore("cdk.context.json")

project.synth()