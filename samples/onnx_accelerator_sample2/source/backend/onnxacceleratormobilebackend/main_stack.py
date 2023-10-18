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
from aws_cdk import (
  aws_iam as iam,
  aws_ec2 as ec2,
  Stack,
  CfnOutput,
  aws_sagemaker as sagemaker,
  aws_events as events,
  aws_s3 as s3,
  aws_lambda as _lambda,
  Aws,
  aws_logs as logs,
  aws_codebuild as cbuild,
  aws_events_targets as targets,
  Duration,
  aws_s3_deployment,
  aws_cloudwatch as cloudwatch
)
from constructs import Construct

import onnxacceleratormobilebackend.sagemakerstudio as sagemakerstudio
import onnxacceleratormobilebackend.cognito.cognito_construct as cognito_construct
import onnxacceleratormobilebackend.api.apigateway_construct as api_gateway_construct

class MainStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    ####################################
    #### Sagemaker Studio and users  ###
    ####################################
    role_sagemaker_studio_domain = iam.Role(self, 'RoleForSagemakerStudioUsers',
                                            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com'),
                                            role_name="RoleSagemakerStudioUsers",
                                            managed_policies=[
                                              iam.ManagedPolicy.from_managed_policy_arn(self,
                                                                                        id="SagemakerReadAccess",
                                                                                        managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess")
                                            ])
    self.role_sagemaker_studio_domain = role_sagemaker_studio_domain
    self.sagemaker_domain_name = "DomainForSagemakerStudio"

    default_vpc_id = ec2.Vpc.from_lookup(self, "DefaultVPC", is_default=True)

    self.vpc_id = default_vpc_id.vpc_id
    self.public_subnet_ids = [public_subnet.subnet_id for public_subnet in default_vpc_id.public_subnets]    
    my_sagemaker_domain = sagemakerstudio.SagemakerStudioDomainConstruct(self, "mySagemakerStudioDomain",
                                                                                  sagemaker_domain_name=self.sagemaker_domain_name,
                                                                                  vpc_id=self.vpc_id,
                                                                                  subnet_ids=self.public_subnet_ids,
                                                                                  role_sagemaker_studio_users=self.role_sagemaker_studio_domain)    
    
    _team = "datascientist-team-A"
    
    my_default_datascience_user = sagemakerstudio.SagemakerStudioUserConstruct(self,
                                                                                _team,
                                                                                sagemaker_domain_id=my_sagemaker_domain.sagemaker_domain_id,
                                                                                user_profile_name=_team)
    CfnOutput(self, f"cfnoutput{_team}",
              value=my_default_datascience_user.user_profile_arn,
              description="The User Arn team domain ID",
              export_name=F"UserArn{_team}")

    CfnOutput(self, "DomainIdSagemaker",
                  value=my_sagemaker_domain.sagemaker_domain_id,
                  description="The sagemaker domain ID",
                  export_name="DomainIdSagemaker"
                  )
    
    # Create the model registry in Sagemaker
    cfn_model_package_group = sagemaker.CfnModelPackageGroup(self, "ImageClassificationModelPackageGroup",
    model_package_group_name="modelPackageImageClassification",
    model_package_group_description="modelPackageGroupDescription"
    )

    ####################################
    #### DEPLOYMENT PACKAGE STEPS ######
    ####################################

    # Create the S3 bucket which will be used for storing the deployment package
    deployment_bucket = s3.Bucket(self, "Bucket",
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        encryption=s3.BucketEncryption.S3_MANAGED,
        bucket_name="onnxacceleratordeploymentbucket"+Aws.ACCOUNT_ID
    )

    CfnOutput(self, "DeploymentPackageS3BucketName",
                  value=deployment_bucket.bucket_name,
                  description="The S3 bucket containing the deployment artifacts for devices",
                  export_name="DeploymentS3BucketName"
                  )
    
    # create s3 bucket for codebuild input artifacts: codebuild needs to run some scripts
    artifacts_bucket = s3.Bucket(self, "artifacts-codebuild-input-bucket",
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        encryption=s3.BucketEncryption.S3_MANAGED,
        bucket_name="onnxacceleratorcodebuildinputbucket"+Aws.ACCOUNT_ID)
    
    CfnOutput(self, "CodeBuildInputArtifactsS3BucketName",
                  value=artifacts_bucket.bucket_name,
                  description="The S3 bucket containing the input artifacts for codebuild",
                  export_name="CodeBuildInputArtifactsS3BucketName"
                  )
    
    #upload the assets which will be used by codebuild to create the deployment package
    aws_s3_deployment.BucketDeployment(self, "DeployCodeBuildInputArtifacts",
        sources=[aws_s3_deployment.Source.asset("./onnxacceleratormobilebackend/codebuild")],
        destination_bucket=artifacts_bucket
    )
  
    # Create the codebuild project
    build_project = cbuild.Project(self, "packageonnxmodel",
        environment=cbuild.BuildEnvironment(
            build_image=cbuild.LinuxBuildImage.STANDARD_3_0,
        ),
        project_name="onnxmodelpackagebuilder",
        timeout=Duration.hours(1),  
        build_spec=cbuild.BuildSpec.from_object({
            "version": "0.2",
            "phases": {    
                "install": {
                    "runtime-versions":{
                        "python": 3.9
                    },
                },
                "build": { 
                    "commands": [
                        "pip3 install torch==1.11.0",
                        "pip3 install numpy==1.24.2",
                        "pip3 install torchvision==0.12.0",
                        "pip3 install onnx==1.13.1",
                        "pip3 install onnxruntime==1.13.1",
                        "aws s3 cp s3://$S3_ARTIFACTS_BUCKET/$S3_ARTIFACTS_OBJECT $S3_ARTIFACTS_OBJECT", # we pull the script which will be used to build our deployment package,
                        "python $S3_ARTIFACTS_OBJECT", # run the script to build the deployment package
                        "cp *.onnx /tmp", # the generated onnx file is copied to the folder used to copy artifacts
                    ]
                }
            },
            "artifacts": {
                "files": [
                    "*.onnx",
                ],
                "base-directory": "/tmp",
                "discard-paths": "yes",
            }
        }),
        artifacts=cbuild.Artifacts.s3(
            bucket=deployment_bucket,
            include_build_id=True,
            package_zip=False,
            identifier="AddArtifact1"
        )
    )

    # codebuild will get data from the model registry, thus it needs permission for that
    build_project.add_to_role_policy(iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=[
        'sagemaker:DescribeModelPackage'
      ],
      resources=[
        'arn:aws:sagemaker:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':model-package/'+cfn_model_package_group.model_package_group_name+'/*'
      ]
    ))

    # grant codebuild rights to download the model tar gz from s3 (created in sagemaker studio).
    # This bucket doesn't exist right now as it is created by sagemaker. We use here the default bucket, where the name follows the following convention:
    # "If not provided, a default bucket will be created based on the following format: “sagemaker-{region}-{aws-account-id}”.""
    build_project.add_to_role_policy(iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=[
        's3:GetObject*',
        's3:GetBucket*',
        's3:List*'
      ],
      resources=[
        'arn:aws:s3:::sagemaker-'+ Aws.REGION+'-'+ Aws.ACCOUNT_ID+'/*'
      ]
    ))
    # grant read access of the artifacts bucket to the codebuild role      
    artifacts_bucket.grant_read(build_project.role)
    # grant write access to the build step so it can push the deployment package
    deployment_bucket.grant_read_write(build_project)

    # Create the eventbridge rule which will trigger the pipeline
    exportRule = events.Rule(
            self,
            "ExportAndOptimizeRule",
            rule_name=f"sagemaker-ExportAndOptimizeRule",
            description="Rule to trigger a new deployment when a model changes status",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail_type=["SageMaker Model Package State Change"],
                detail={
                    "ModelPackageGroupName": [
                        cfn_model_package_group.model_package_group_name,
                    ],
                    "ModelApprovalStatus": [
                        "Approved",
                    ],
                },
            ),
        )
    
    exportRule.add_target(targets.CodeBuildProject(build_project,
                                                   event=events.RuleTargetInput.from_object({ # let's override the env variables since we need info from the event context
                                                        "environmentVariablesOverride": [
                                                                {
                                                                    "name": 'S3_ARTIFACTS_BUCKET',
                                                                    "value": artifacts_bucket.bucket_name,
                                                                    "type": 'PLAINTEXT',
                                                                },
                                                                {
                                                                    "name": 'S3_ARTIFACTS_OBJECT',
                                                                    "value": 'build_deployment_package.py',
                                                                    "type": 'PLAINTEXT',
                                                                },
                                                                {
                                                                    "name": 'MODEL_PACKAGE_ARN',
                                                                    "value": events.EventField.from_path('$.detail.ModelPackageArn'), # arn of the group model package
                                                                    "type": 'PLAINTEXT',
                                                                },
                                                                {
                                                                    "name": 'DEPLOYMENT_BUCKET_NAME',
                                                                    "value": deployment_bucket.bucket_name, # The S3 bucket where output artifacts will be uploaded
                                                                    "type": 'PLAINTEXT',
                                                                }
                                                            ],
                                                    })
                                                )
    ) # The event is what is passed to the startbuild api https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_events/RuleTargetInput.html
    # event content: https://docs.aws.amazon.com/sagemaker/latest/dg/automating-sagemaker-with-eventbridge.html#eventbridge-model-package
    # start build api syntax: https://docs.aws.amazon.com/codebuild/latest/APIReference/API_StartBuild.html#CodeBuild-StartBuild-request-environmentVariablesOverride

    ####################################
    ########## API GATEWAY #############
    ####################################

    cognito_construct_output = cognito_construct.CognitoConstruct(
            self,
            "Cognito",
            region=Aws.REGION,
        )
    
    cognito_user_pool = cognito_construct_output.getUserPool()
    cognito_user_pool_client = cognito_construct_output.getUserPoolClient()

    # Create the S3 bucket which will be used for storing the input images
    input_images_bucket = s3.Bucket(self, "BucketInput",
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        encryption=s3.BucketEncryption.S3_MANAGED,
        bucket_name="onnxacceleratorinputimagesbucket"+Aws.ACCOUNT_ID,
        cors=[s3.CorsRule(
            allowed_methods=[s3.HttpMethods.POST],
            allowed_origins=["*"]
          )
        ]
    )

    CfnOutput(self, "InputImagesS3BucketName",
                  value=deployment_bucket.bucket_name,
                  description="The S3 bucket containing the input images from devices",
                  export_name="InputImagesS3BucketName"
                  )

    apigw_construct = api_gateway_construct.API(
      self, 
      "ApiGwConstruct", 
      input_images_bucket=input_images_bucket, 
      model_deployment_bucket=deployment_bucket,
      cognito_user_pool=cognito_user_pool,
      cognito_user_pool_client=cognito_user_pool_client
    )

    ####################################
    #### DATA VISUALIZATION PIPELINE ###
    ####################################
        
    # add a dashboard with some sample queries
    dashboard = cloudwatch.Dashboard(self, "MyDashboard",
      dashboard_name="InspectionMetrics",
      period_override=cloudwatch.PeriodOverride.AUTO,
    )

    logs_group = apigw_construct.getLogsIngestionLogsGroup()
    log_stream = apigw_construct.getLogsIngestionLogStream()

    dashboard.add_widgets(cloudwatch.LogQueryWidget(
      log_group_names=[logs_group.log_group_name],
      width= 24,
      view=cloudwatch.LogQueryVisualizationType.LINE,
      title="Anomalies count",
      query_lines=[
        "parse '* * * * * * *' as ts, username, model_name, label, score, inputImageUrl, inputImageKey",
        "filter @logStream like /"+log_stream.log_stream_name+"/",
        "sort @timestamp desc",
        "stats count() by bin(30s)"
      ]
    ))
   
    cloudwatchDashboardURL = 'https://'+Aws.REGION+'.console.aws.amazon.com/cloudwatch/home?region='+Aws.REGION+'#dashboards:name='+dashboard.dashboard_name
    CfnOutput(self, "DashboardOutput",
              value=cloudwatchDashboardURL,
              description="URL of Sample CloudWatch Dashboard",
              export_name="SampleCloudWatchDashboardURL"
              )
    
    CfnOutput(
          self,
          "RegionName",
          value=self.region,
          export_name=f"{Stack.of(self).stack_name}RegionName",
    )
