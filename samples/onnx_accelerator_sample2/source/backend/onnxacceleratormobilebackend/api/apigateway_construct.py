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

import aws_cdk.aws_apigatewayv2_alpha as apigatewayv2_alpha
from aws_cdk.aws_apigatewayv2_integrations_alpha import HttpLambdaIntegration
from aws_cdk.aws_apigatewayv2_authorizers_alpha import HttpUserPoolAuthorizer
from aws_cdk import (
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_logs as logs,
    RemovalPolicy,
    aws_cognito as cognito_,
    aws_logs as logs,
    aws_iam as iam,
    Aws,
    Duration,
    CfnOutput,
    Stack
)
from constructs import Construct

class API(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        *,
        input_images_bucket: s3.Bucket,
        model_deployment_bucket: s3.Bucket,
        cognito_user_pool: cognito_.CfnUserPool,
        cognito_user_pool_client: cognito_.CfnUserPoolClient
    ):
        super().__init__(scope, id_)

        #########################################
        ########### Create the api gateway ######
        #########################################

        authorizer = HttpUserPoolAuthorizer("OnnxAuthorizer", 
                                            pool=cognito_user_pool,
                                            user_pool_clients=[cognito_user_pool_client])

        api = apigatewayv2_alpha.HttpApi(self, 
                                         "HttpApi", 
                                         cors_preflight=apigatewayv2_alpha.CorsPreflightOptions(
                                            allow_headers=["Authorization", "content-type", "x-amz-date", "x-api-key"],
                                            allow_methods=[apigatewayv2_alpha.CorsHttpMethod.GET, apigatewayv2_alpha.CorsHttpMethod.HEAD, apigatewayv2_alpha.CorsHttpMethod.OPTIONS, apigatewayv2_alpha.CorsHttpMethod.POST],
                                            allow_origins=["*"],
                                            max_age=Duration.days(10)
                                        )
        )

        CfnOutput(self, "ApiGatewayEndpoint",
              value=api.api_endpoint,
              description="API Gateway endpoint",
              export_name=f"{Stack.of(self).stack_name}{id_}Endpoint")

        ##################################################
        ####### Pre-signed URL model artifacts ###########
        ##################################################

        # Set Lambda Logs Retention and Removal Policy
        logs.LogGroup(
            self,
            'logs_model_url',
            log_group_name = f"/aws/lambda/modelurl",
            removal_policy = RemovalPolicy.DESTROY,
            retention = logs.RetentionDays.ONE_WEEK
        )

        function_get_model_url = lambda_.Function(self, "lambda_function_model_url",
                                            runtime=lambda_.Runtime.PYTHON_3_9,
                                            handler="lambda.handler",
                                            code=lambda_.Code.from_asset("functions/model_presigned_url/src"),
                                            function_name="onnx_model_presigned_url",
                                            environment={
                                                'DEPLOYMENT_BUCKET': model_deployment_bucket.bucket_name,
                                            }
        )

        api.add_routes(
            integration=HttpLambdaIntegration("GetOnnxModelIntegration", function_get_model_url),
            path="/getmodelurl",
            methods=[apigatewayv2_alpha.HttpMethod.GET],
            authorizer=authorizer
        )

        model_deployment_bucket.grant_read(function_get_model_url)

        ##################################################
        ####### Pre-signed URL upload image ###########
        ##################################################

        # Set Lambda Logs Retention and Removal Policy
        logs.LogGroup(
            self,
            'logs_upload_image_url',
            log_group_name = f"/aws/lambda/imageurl",
            removal_policy = RemovalPolicy.DESTROY,
            retention = logs.RetentionDays.ONE_WEEK
        )

        function_upload_image_url = lambda_.Function(self, "lambda_function_upload_image_url",
                                            runtime=lambda_.Runtime.PYTHON_3_9,
                                            handler="lambda.handler",
                                            code=lambda_.Code.from_asset("functions/upload_image_url/src"),
                                            function_name="upload_image_presigned_url",
                                            environment={
                                                'INPUT_IMAGES_BUCKET': input_images_bucket.bucket_name,
                                            }
        )

        api.add_routes(
            integration=HttpLambdaIntegration("UploadImageIntegration", function_upload_image_url),
            path="/getuploadurl",
            methods=[apigatewayv2_alpha.HttpMethod.GET],
            authorizer=authorizer
        )

        input_images_bucket.grant_read(function_upload_image_url)
        # the lambda generating the post presigned url needs to have correct permissions to post an object, otherwise the client will get a 403
        input_images_bucket.grant_put(function_upload_image_url, objects_key_pattern="new/*")

        ##################################
        ####### Logs ingestion ###########
        ##################################

        # Set Lambda Logs Retention and Removal Policy
        logs_ingestion_group_name = f"/aws/lambda/logsingestion"

        self.logs_ingestion_lgroup = logs.LogGroup(
            self,
            'logs_ingestion',
            log_group_name = logs_ingestion_group_name,
            removal_policy = RemovalPolicy.DESTROY,
            retention = logs.RetentionDays.ONE_WEEK
        )

        self.log_stream_infer = logs.LogStream(self, "inference_log_stream",
            log_group=self.logs_ingestion_lgroup,
            log_stream_name="inference",
            removal_policy=RemovalPolicy.DESTROY
        )

        function_ingestion_logs = lambda_.Function(self, "lambda_function_logs_ingestion",
                                            runtime=lambda_.Runtime.PYTHON_3_9,
                                            handler="lambda.handler",
                                            code=lambda_.Code.from_asset("functions/logsingestion/src"),
                                            function_name="logs_ingestion",
                                            environment={
                                                'LOG_GROUP_NAME': self.logs_ingestion_lgroup.log_group_name,
                                                'LOG_STREAM_INFERENCE_NAME': self.log_stream_infer.log_stream_name,
                                            })

        function_ingestion_logs.add_to_role_policy(iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            'logs:PutLogEvents',
            'logs:DescribeLogStreams'
        ],
        resources=[
            'arn:aws:logs:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':log-group:'+self.logs_ingestion_lgroup.log_group_name+':log-stream:',
            'arn:aws:logs:'+ Aws.REGION+':'+ Aws.ACCOUNT_ID+':log-group:'+self.logs_ingestion_lgroup.log_group_name+':log-stream:'+self.log_stream_infer.log_stream_name,
        ]
        ))

        api.add_routes(
            integration=HttpLambdaIntegration("MobilePredictionLogs", function_ingestion_logs),
            path="/postlogs",
            methods=[apigatewayv2_alpha.HttpMethod.POST],
            authorizer=authorizer
        )

    def getLogsIngestionLogsGroup(self):
        return self.logs_ingestion_lgroup
    
    def getLogsIngestionLogStream(self):
        return self.log_stream_infer
