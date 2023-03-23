# Onnx ML at the edge

This code sample provides an end-to-end solution that manages the lifecycle of ML models deployed to a simulated wind turbine fleet. We'll use Amazon SageMaker to prepare a Machine Learning (ML) model and AWS IoT services, both AWS IoT Jobs and AWS IoT Greengrass v2 to deploy and run this model to an edge device (Raspberry Pi). To be agnostic of the different device frameworks and ML accelerator we leverage [ONNX Runtime](https://onnxruntime.ai/).

Using a Machine Learning model ([Autoencoder](https://en.wikipedia.org/wiki/Autoencoder)) you can analyze the turbine sensors data and detect anomalies. This technique is important to improve the maintenance process and reduce the operational cost.

This code sample is a variant of the solution presented in [this](https://aws.amazon.com/blogs/machine-learning/monitor-and-manage-anomaly-detection-models-on-a-fleet-of-wind-turbines-with-amazon-sagemaker-edge-manager/) blog post, without using Sagemaker Edge Manager. The blog post contains useful information about the custom ML model trained.

Two options are available to deploy this code sample: 
- deploy using [AWS IoT Jobs](https://docs.aws.amazon.com/iot/latest/developerguide/iot-jobs.html): once a specific model version is approved by an IIoT Engineer in the Amazon Sagemaker model registry, a build step exports the ML model to the ONNX format, and an AWS Lambda function creates an AWS IoT job targetting all devices.
- deploy using [AWS IoT Greengrass v2](https://aws.amazon.com/greengrass/): once a specific model version is approved by an IIoT Engineer in the Amazon Sagemaker model registry, a build step creates three AWS IoT Greengrass components, and an AWS Lambda function creates a Greengrass deployment targetting all Greengrass core devices.

Chose one of the option above and follow the dedicated steps as desribed below

## Option 1 : Deploy using AWS IoT Jobs

Documentation is located [here](./IoTJobs.md)

## Option 2 : Deploy using AWS IoT Greengrass V2

Documentation is located [here](./Greengrass.md)

# Content Security Legal Disclaimer
The sample code; software libraries; command line tools; proofs of concept; templates; or other related technology (including any of the foregoing that are provided by our personnel) is provided to you as AWS Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

# Operational Metrics Collection
This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. Data collection is subject to the AWS Privacy Policy (https://aws.amazon.com/privacy/). To opt out of this feature, simply remove the tag(s) starting with “uksb-” or “SO” from the description(s) in any CloudFormation templates or CDK TemplateOptions (app.py).