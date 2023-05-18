# Onnx ML in the browser - Backend

# Getting started

## Pre-requisites

- An AWS account. We recommend to deploy this solution in a new account
- [AWS CLI](https://aws.amazon.com/cli/): configure your credentials

```
aws configure --profile [your-profile] 
AWS Access Key ID [None]: xxxxxx
AWS Secret Access Key [None]:yyyyyyyyyy
Default region name [None]: us-east-1 
Default output format [None]: json
```

- Node.js: v18.12.1
- [AWS CDK](https://github.com/aws/aws-cdk/releases/tag/v2.68.0): 2.68.0
- jq: jq-1.6

## Deploy the solution

This project is built using [Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/) and [projen](https://github.com/projen/projen). See [Getting Started With the AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for additional details and prerequisites. When running the commands below, projen will run ```python``` and not ```python3```, so make sure your ```python``` command runs the correct Python version. 

1. Clone this repository.
    ```shell
    $ git clone https://github.com/aws-samples/ml-edge-getting-started/
    ```

2. Enter the code sample backend directory.
    ```shell
    $ cd samples/onnx_accelerator_sample2/source/backend
    ```
 
3. Activate virtualenv, install dependencies and synthesize.
    ```shell
    $ npx projen build
    ```

4. Boostrap AWS CDK resources on the AWS account.
    ```shell
    $ npx cdk bootstrap
    ```

5. Deploy the sample in your account
    ```shell
    $ npx cdk deploy
    ```

Once the stack is deployed, in the AWS console go to Cloudformation -> Stacks -> onnxacceleratormobilebackend-dev -> Outputs

The following outputs are generated:
- ```cfnoutputdatascientistteamA```	: The User Arn user for the SageMaker user representing the Data science team
- ```ApiGwConstructApiGatewayEndpoint*``` : The API Gateway endpoint
- ```CognitoIdentityPoolId``` : The id of the identity pool, used for authorization (access control). Users can obtain temporary AWS credentials to access AWS services, such as Amazon S3
- ```CognitoUserPoolClientId``` : Id of the user pool client, connected to the user pool. This id is used by applications to access the user pool
- ```CognitoUserPoolId``` : Id of the cognito user pool, used for authentication (identity verification)
- ```CodeBuildInputArtifactsS3BucketName```	: The S3 bucket containing the input artifacts for codebuild (python script)	
- ```DashboardOutput```	: URL of the Cloudwatch dashboard providing visualization of anomalies and raw data
- ```InputImagesS3BucketName``` : The S3 bucket containing the input images from devices, used for inference
- ```DeploymentPackageS3BucketName``` : The S3 bucket containing the deployment artifacts for edge devices (onnx exported model + job json file)
- ```DomainIdSagemaker``` : The SageMaker domain ID

> **Note**
> SageMaker Studio will be provisioned using the default VPC, thus it needs to exist. If you want to use a different VPC, udpate ```default_vpc_id = ec2.Vpc.from_lookup(self, "DefaultVPC", is_default=True)``` in [main_stack.py](./onnxacceleratorsampleone/main_stack.py)

## Notebook

Once your application is correctly deployed, you can deploy the ML model.

1. In the AWS console, go to Amazon SageMaker and select Studio. 
2. In the Get Started right panel, select the ```datascientist-team-a``` and click Open Studio.
3. On the left menu bar, select Git and Clone a Repository
4. In the drop-down enter https://github.com/aws-samples/ml-edge-getting-started.git
5. Select the explorer view, select ```ml-edge-getting-started/samples/onnx_accelerator_mobile/notebooks``` and open the notebook ```image_classification.ipynb```
8. Execute the cells in the notebook to train the model, and register it in the Amazon SageMaker Model registry. The model artifacts will also be stored in the SageMaker default Amazon Simple Storage Service (S3) bucket.
9. On the left menu bar, select ```Home``` -> ```Models``` -> ```Model registry```
10. Double click the ```modelPackageImageClassification``` model group name
11. Select the model version you just created, double click on it and update its status in the top right corner from ```PendingManualApproval``` to ```Approved```

## Model export and deployment

Approving the model version in the Amazon SageMaker Model registry triggers a codebuild step. The Eventbridge rule sends an event to Codebuild with information about the model you just approved. A new build step is then triggered, pulling the model artifact and exporting it to the ONNX format. This step is performed in [build_deployment_package.py](./onnxacceleratormobilebackend/codebuild/build_deployment_package.py). The script then runs an inference session using the ONNX Runtime to compare results of the onnx model with the PyTorch one. The exported model is saved in the deployment package S3 bucket.

Because the model is loaded and run on device, the model must fit on the device disk and be able to be loaded into the device’s memory.

You can modify the script to quantize the model if you want to reduce its size. An example is available through the [official onnx code repo](https://github.com/microsoft/onnxruntime-inference-examples/blob/main/quantization/notebooks/imagenet_v2/mobilenet.ipynb). The quality of the prediction will also be reduced.

## Visualization

Access the Amazon Cloudwatch dashboard using the URL output provided by your cloudformation stack. One widget is available with sample queries to visualize useful information. You can modify the widget query in [main_stack.py](./onnxacceleratormobilebackend/main_stack.py) if you want to display different data.

You will need to deploy the front-end and run an inference on your device to start visualizing some data in the dashboard.

## Clean up

Do not forget to delete the stack to avoid unexpected charges

First make sure to remove all data (model versions) from the model registry. Then:

```shell
    $ cdk destroy onnxacceleratormobilebackend-dev
```

Then in the AWS console delete the S3 buckets