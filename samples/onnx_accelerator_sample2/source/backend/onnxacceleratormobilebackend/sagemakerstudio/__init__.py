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

from typing import List

from aws_cdk import (
	aws_iam as iam
)

from constructs import Construct

import aws_cdk.cloudformation_include as cfn_inc
import os.path as path
import typing


class SagemakerStudioDomainConstruct(Construct):

	def __init__(self, scope: Construct, construct_id: str, *,
	             sagemaker_domain_name: str,
	             vpc_id: str,
	             subnet_ids: typing.List[str],
	             role_sagemaker_studio_users: iam.IRole,
	             **kwargs
	             ) -> None:
		super().__init__(scope, construct_id)

		my_sagemaker_domain = cfn_inc.CfnInclude(self, construct_id,
		                                         template_file=path.join(path.dirname(path.abspath(__file__)),
		                                                                 "sagemakerStudioCloudFormationStack/sagemaker-domain-template.yaml"),
		                                         parameters={
			                                         "auth_mode": "IAM",
			                                         "domain_name": sagemaker_domain_name,
			                                         "vpc_id": vpc_id,
			                                         "subnet_ids": subnet_ids,
			                                         "default_execution_role_user": role_sagemaker_studio_users.role_arn,
		                                         })
		self.sagemaker_domain_id = my_sagemaker_domain.get_resource('SagemakerDomainCDK').ref

#https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-userprofile.html
class SagemakerStudioUserConstruct(Construct):

	def __init__(self, scope: Construct,
	             construct_id: str, *,
	             sagemaker_domain_id: str,
	             user_profile_name: str,
	             **kwargs) -> None:
		super().__init__(scope, construct_id)

		my_sagemaker_studio_user_template = cfn_inc.CfnInclude(self, construct_id,
		                                                       template_file=path.join(
			                                                       path.dirname(path.abspath(__file__)),
			                                                       "sagemakerStudioCloudFormationStack/sagemaker-user-template.yaml"),
		                                                       parameters={
			                                                       "sagemaker_domain_id": sagemaker_domain_id,
			                                                       "user_profile_name": user_profile_name
		                                                       },
		                                                       preserve_logical_ids=False)
		self.user_profile_arn = my_sagemaker_studio_user_template.get_resource('SagemakerUser').get_att(
			'UserProfileArn').to_string()