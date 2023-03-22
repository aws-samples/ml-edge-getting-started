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
  RemovalPolicy,
  aws_sagemaker as sagemaker,
  aws_events as events,
  aws_s3 as s3,
  aws_lambda as _lambda,
  Aws,
  aws_iot as iot,
  aws_logs as logs,
  aws_codebuild as cbuild,
  aws_events_targets as targets,
  Duration,
  aws_s3_notifications,
  aws_s3_deployment,
  aws_cloudwatch as cloudwatch
)
from constructs import Construct

import onnxacceleratorsampleone.sagemakerstudio as sagemakerstudio

class MainStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    use_greengrass = self.node.try_get_context('use_greengrass')

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
    
    teams_to_add_in_sagemaker_studio = ["datascientist-team-A", "IIoT-engineering-team"]

    for _team in teams_to_add_in_sagemaker_studio:
    
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
    cfn_model_package_group = sagemaker.CfnModelPackageGroup(self, "TurbineModelPackageGroup",
    model_package_group_name="modelPackageGroupTurbine",
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
    
    # create a role for iot job to download job file from S3 with a pre-signed url
    iot_job_s3_role = iam.Role(self, 'RoleForIoTJobAccessS3JobFiles',
                        assumed_by=iam.ServicePrincipal('iot.amazonaws.com'),
                        role_name="RoleForIoTJobAccessS3JobFiles",
                        managed_policies=[
                            iam.ManagedPolicy.from_managed_policy_arn(self,
                                                                    id="AWSIoTThingsRegistration",
                                                                    managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration"),
                            iam.ManagedPolicy.from_managed_policy_arn(self,
                                                                    id="AWSIoTLogging",
                                                                    managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSIoTLogging"),
                            iam.ManagedPolicy.from_managed_policy_arn(self,
                                                                    id="AmazonS3ReadOnlyAccess",
                                                                    managed_policy_arn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"),
                                                                    
                        ],
                        path="/"
                        )

    iot_thing_group_name = self.node.try_get_context('thing_group_name')

    if use_greengrass is True:
      # attach the lambda which will be triggered everytime there is a new object created
      function_iot_deployment = _lambda.Function(self, "lambda_function",
                                                  runtime=_lambda.Runtime.PYTHON_3_9,
                                                  handler="lambda.handler",
                                                  code=_lambda.Code.from_asset("functions/greengrassdeploymentcreator/src"),
                                                  function_name="greengrass_deployment",
                                                  environment={
                                                      'THING_GROUP_NAME': iot_thing_group_name
                                                  }
                                                  )
      
      function_iot_deployment.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
          'greengrass:ListComponents',
          'greengrass:GetDeployment',
          'greengrass:CreateDeployment',
          'greengrass:ListDeployments',
          'greengrass:ListComponentVersions'

        ],
        resources=[
          'arn:aws:greengrass:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':components:*',
          'arn:aws:greengrass:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':/greengrass/groups/*',
          'arn:aws:greengrass:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':deployments',
          'arn:aws:greengrass:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':deployments:*'
        ]
      ))

      function_iot_deployment.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
          'iot:DescribeJob',
          'iot:CancelJob',
          'iot:CreateJob'

        ],
        resources=[
          'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':job/*',
          'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':thinggroup/*'
        ]
      ))
    else:
      # attach the lambda which will be triggered everytime there is a new object created
      function_iot_deployment = _lambda.Function(self, "lambda_function",
                                                  runtime=_lambda.Runtime.PYTHON_3_9,
                                                  handler="lambda.handler",
                                                  code=_lambda.Code.from_asset("functions/iotjobcreator/src"),
                                                  function_name="iot_job_deployment",
                                                  environment={
                                                      'THING_GROUP_NAME': iot_thing_group_name,
                                                      'ARN_IOT_PROVISIONING_ROLE': iot_job_s3_role.role_arn
                                                  }
                                                  )

      function_iot_deployment.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
          'iam:PassRole'
        ],
        resources=[
          'arn:aws:iam::'+ Aws.ACCOUNT_ID+':role/'+iot_job_s3_role.role_name
        ]
      ))

      function_iot_deployment.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
          'iot:CreateJob'
        ],
        resources=[
          'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':job/*',
          'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':thing/*',
          'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':thinggroup/*',
          'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':jobtemplate/*'
        ]
      ))

    function_iot_deployment.add_to_role_policy(iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=[
        'iot:DescribeThingGroup'
      ],
      resources=[
        'arn:aws:iot:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':thinggroup/'+iot_thing_group_name
      ]
    ))
    
    logs.LogGroup(
        self,
        'logs_iot_lambda',
        log_group_name = f"/aws/lambda/{function_iot_deployment.function_name}",
        removal_policy = RemovalPolicy.DESTROY,
        retention = logs.RetentionDays.ONE_WEEK
    )
    
    new_deployment_package_notification = aws_s3_notifications.LambdaDestination(function_iot_deployment)

    deployment_bucket.add_event_notification(
      s3.EventType.OBJECT_CREATED, 
      new_deployment_package_notification,
      s3.NotificationKeyFilter(suffix="json"))
  
    deployment_bucket.grant_read(function_iot_deployment)
    
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
    if use_greengrass is True:
      aws_s3_deployment.BucketDeployment(self, "DeployCodeBuildInputArtifacts",
          sources=[aws_s3_deployment.Source.asset("./onnxacceleratorsampleone/with_ggv2")],
          destination_bucket=artifacts_bucket
      )

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
                        "pip3 install git+https://github.com/aws-greengrass/aws-greengrass-gdk-cli.git@v1.2.1",
                        "pip3 install torch==1.13.1",
                        "pip3 install numpy==1.24.2",
                        "aws s3 cp s3://$S3_ARTIFACTS_BUCKET/$S3_ARTIFACTS_OBJECT $S3_ARTIFACTS_OBJECT",
                        "aws s3 cp s3://$S3_ARTIFACTS_BUCKET/components ./ --recursive", # we pull all the artifacts used to build our deployment package,
                        "touch trigger.json", # empty file, will be used to trigger a deployment
                        "cp trigger.json /tmp",
                        "python $S3_ARTIFACTS_OBJECT", # run the script to build the deployment package
                        "cd ./aws.samples.windturbine.detector.venv",
                        "gdk component build -d",
                        "gdk component publish --debug --bucket $DEPLOYMENT_BUCKET_NAME",
                        "cd ../aws.samples.windturbine.model",
                        "gdk component build -d",
                        "gdk component publish --debug --bucket $DEPLOYMENT_BUCKET_NAME",
                        "cd ../aws.samples.windturbine.detector",
                        "gdk component build",
                        "gdk component publish --debug --bucket $DEPLOYMENT_BUCKET_NAME",
                    ]
                }
            },
            "artifacts": {
                "files": [
                    "trigger.json"
                ],
                "base-directory": "/tmp",
                "discard-paths": "yes",
            }
        }),
        artifacts=cbuild.Artifacts.s3(
            bucket=deployment_bucket,
            include_build_id=True,
            package_zip=False, # we don't want to zip everything as we create a job file
            identifier="AddArtifact1"
        )
      )

      build_project.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
          'greengrass:CreateComponentVersion',
          'greengrass:ListComponentVersions'
        ],
        resources=[
          'arn:aws:greengrass:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':components:*'
        ]
      ))

      build_project.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
          's3:CreateBucket'
        ],
        resources=[
          deployment_bucket.bucket_arn # gdk needs to have the right to create a bucket even though the already exists, so we give right to create only the bucket we already created
        ]
      ))

    else:
      aws_s3_deployment.BucketDeployment(self, "DeployCodeBuildInputArtifacts",
          sources=[aws_s3_deployment.Source.asset("./onnxacceleratorsampleone/without_ggv2")],
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
                          "pip3 install torch==1.13.1",
                          "pip3 install numpy==1.24.2",
                          "aws s3 cp s3://$S3_ARTIFACTS_BUCKET/$S3_ARTIFACTS_OBJECT $S3_ARTIFACTS_OBJECT", # we pull the script which will be used to build our deployment package,
                          "python $S3_ARTIFACTS_OBJECT", # run the script to build the deployment package
                          "cp *.onnx /tmp", # the generated onnx file is copied to the folder used to copy artifacts
                          "cp job.json /tmp",
                      ]
                  }
              },
              "artifacts": {
                  "files": [
                      "*.onnx",
                      "job.json"
                  ],
                  "base-directory": "/tmp",
                  "discard-paths": "yes",
              }
          }),
          artifacts=cbuild.Artifacts.s3(
              bucket=deployment_bucket,
              include_build_id=True,
              package_zip=False, # we don't want to zip everything as we create a job file
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
        'arn:aws:sagemaker:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':model-package/'+cfn_model_package_group.model_package_group_name.lower()+'/*' #the model group name needs to be lowercase
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
    #### DATA VISUALIZATION PIPELINE ###
    ####################################

    # Set Lambda Logs Retention and Removal Policy
    edge_logs_group_name = f"/aws/lambda/iotlogstocloudwatch"

    edge_logs_group = logs.LogGroup(
        self,
        'logs',
        log_group_name = edge_logs_group_name,
        removal_policy = RemovalPolicy.DESTROY,
        retention = logs.RetentionDays.ONE_WEEK
    )

    # create 2 logs streams
    log_stream_infer = logs.LogStream(self, "inference_log_stream",
        log_group=edge_logs_group,
        log_stream_name="inference",
        removal_policy=RemovalPolicy.DESTROY
    )

    log_stream_raw = logs.LogStream(self, "raw_data_log_stream",
        log_group=edge_logs_group,
        log_stream_name="rawdata",
        removal_policy=RemovalPolicy.DESTROY
    )

    function_edge_logs = _lambda.Function(self, "lambda_function_edge_logs",
                                        runtime=_lambda.Runtime.PYTHON_3_9,
                                        handler="lambda.handler",
                                        code=_lambda.Code.from_asset("functions/edgeapplogs/src"),
                                        function_name="iotlogstocloudwatch",
                                        environment={
                                            'LOG_GROUP_NAME': edge_logs_group.log_group_name,
                                            'LOG_STREAM_INFERENCE_NAME': log_stream_infer.log_stream_name,
                                            'LOG_STREAM_RAW_DATA_NAME': log_stream_raw.log_stream_name
                                        })

    function_edge_logs.add_to_role_policy(iam.PolicyStatement(
      effect=iam.Effect.ALLOW,
      actions=[
        'logs:PutLogEvents',
        'logs:DescribeLogStreams'
      ],
      resources=[
        'arn:aws:logs:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':log-group:'+edge_logs_group_name+':log-stream:',
        'arn:aws:logs:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':log-group:'+edge_logs_group_name+':log-stream:'+log_stream_infer.log_stream_name,
        'arn:aws:logs:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':log-group:'+edge_logs_group_name+':log-stream:'+log_stream_raw.log_stream_name
      ]
    ))
        
    # IoT Rule with SQL, which invokes a Lambda Function
    topic_name = self.node.try_get_context('devices_logs_topic')
    iot_topic_rule_sql = 'SELECT *, clientid() AS clientid FROM "'+topic_name+'"'
    iot_topic_rule = iot.CfnTopicRule(
        self, "IoTRule",
        topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
            sql=iot_topic_rule_sql,
            actions=[iot.CfnTopicRule.ActionProperty(
                lambda_=iot.CfnTopicRule.LambdaActionProperty(
                    function_arn=function_edge_logs.function_arn
                )
            )],
            aws_iot_sql_version="2016-03-23", # this is important, default version has a bug with nested mqtt data
        ),
    )

    # Lambda Resource Policy allows invocation from IoT Rule 
    function_edge_logs.add_permission(
        "GrantIoTRule",
        principal=iam.ServicePrincipal("iot.amazonaws.com"),
        source_arn=iot_topic_rule.attr_arn
    )

    # add a dashboard with some sample queries
    dashboard = cloudwatch.Dashboard(self, "MyDashboard",
      dashboard_name="WindturbinesAnomalyDetection",
      period_override=cloudwatch.PeriodOverride.AUTO,
    )

    dashboard.add_widgets(cloudwatch.LogQueryWidget(
      log_group_names=[edge_logs_group.log_group_name],
      width= 24,
      view=cloudwatch.LogQueryVisualizationType.LINE,
      title="Voltage Avg",
      query_lines=[
        "parse '* * * * * * * * * * * * * * * * * * * * * *' as ts, device_name, device_ts, device_freemem, rps, wind_speed_rps, voltage, qw, qx, qy, qz, gx, gy, gz, aax,aay,aaz, gearbox_temp, ambient_temp, air_humidity, air_pressure, air_quality",
        "filter @logStream like /"+log_stream_raw.log_stream_name+"/",
        "sort @timestamp desc",
        "limit 20",
        "stats avg(voltage) as voltage_avg by bin(1m)"
      ]
    ))

    dashboard.add_widgets(cloudwatch.LogQueryWidget(
      log_group_names=[edge_logs_group.log_group_name],
      width= 24,
      view=cloudwatch.LogQueryVisualizationType.LINE,
      title="Rotation Avg",
      query_lines=[
        "parse '* * * * * * * * * * * * * * * * * * * * * *' as ts, device_name, device_ts, device_freemem, rps, wind_speed_rps, voltage, qw, qx, qy, qz, gx, gy, gz, aax,aay,aaz, gearbox_temp, ambient_temp, air_humidity, air_pressure, air_quality",
        "filter @logStream like /"+log_stream_raw.log_stream_name+"/",
        "sort @timestamp desc",
        "limit 20",
        "stats avg(rps) as rps_avg, avg(wind_speed_rps) as wind_speed_rps_avg by bin(1m)"
      ]
    ))

    dashboard.add_widgets(cloudwatch.LogQueryWidget(
      log_group_names=[edge_logs_group.log_group_name],
      width= 24,
      view=cloudwatch.LogQueryVisualizationType.LINE,
      title="Vibration Avg",
      query_lines=[
        "parse '* * * * * * * * * * * * * * * * * * * * * *' as ts, device_name, device_ts, device_freemem, rps, wind_speed_rps, voltage, qw, qx, qy, qz, gx, gy, gz, aax,aay,aaz, gearbox_temp, ambient_temp, air_humidity, air_pressure, air_quality",
        "filter @logStream like /"+log_stream_raw.log_stream_name+"/",
        "sort @timestamp desc",
        "limit 20",
        "stats avg(qw) as qw_avg, sum(qx) as qx_avg, avg(qy) as qy_avg,avg(qz) as qz_avg by bin(1m)"
      ]
    ))

    dashboard.add_widgets(cloudwatch.LogQueryWidget(
      log_group_names=[edge_logs_group.log_group_name],
      width= 24,
      view=cloudwatch.LogQueryVisualizationType.LINE,
      title="Anomalies count",
      query_lines=[
        "parse '* * * * * * * * * * * * * * * *' as ts, device_name, model_name, model_version, roll_anom, pitch_anom, yaw_anom, wind_anom, rps_anom, voltage_anom, roll_mae, pitch_mae, yaw_mae, wind_mae, rps_mae, voltage_mae",
        "filter @logStream like /"+log_stream_infer.log_stream_name+"/",
        "sort @timestamp desc",
        "limit 20",
        "stats sum(roll_anom) as roll_anomalies, sum(pitch_anom) as pitch_anomalies, sum(yaw_anom) as yaw_anomalies, sum(wind_anom) as wind_anomalies, sum(rps_anom) as rps_anomalies, sum(voltage_anom) as voltage_anomalies by bin(1m)",
        "sort maxBytes desc"
      ]
    ))
   
    cloudwatchDashboardURL = 'https://'+Aws.REGION+'.console.aws.amazon.com/cloudwatch/home?region='+Aws.REGION+'#dashboards:name='+dashboard.dashboard_name
    CfnOutput(self, "DashboardOutput",
              value=cloudwatchDashboardURL,
              description="URL of Sample CloudWatch Dashboard",
              export_name="SampleCloudWatchDashboardURL"
              )