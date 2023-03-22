import json
import boto3
import os
import urllib.parse
import time

iot_job_client = boto3.client('iot')
greengrass_client = boto3.client('greengrassv2')
thing_group_name = os.environ['THING_GROUP_NAME']
region = os.environ['AWS_REGION']
detector_component_name = 'aws.samples.windturbine.detector'
model_component_name = 'aws.samples.windturbine.model'
detector_venv_component_name = 'aws.samples.windturbine.detector.venv'

def get_newest_component_version(component_name):
    """ Gets the newest version of a component """
    account_id = boto3.client('sts').get_caller_identity()['Account']
    component_arn = 'arn:aws:greengrass:{}:{}:components:{}'.format(region, account_id, component_name)

    try:
        response = greengrass_client.list_component_versions(arn=component_arn)
    except Exception as e:
        print('Failed to get component versions for {}\nException: {}'.format(component_name, e))
        return

    return response['componentVersions'][0]['componentVersion']

def get_deployment(thing_group_arn):
    """ Gets the details of the existing deployment """

    print('Searching for existing deployment for {}'.format(thing_group_arn))

    try:
        # Get the latest deployment for the specified core device name
        response = greengrass_client.list_deployments(
            targetArn=thing_group_arn,
            historyFilter='LATEST_ONLY',
            maxResults=1
        )
    except Exception as e:
        print('Failed to list deployments\nException: {}'.format(e))
        return ''

    # If there is no existing deployment, we will create a new one
    if len(response['deployments']) == 0:
        print('No existing Thing deployment for this thing group. Aborting.')
        return ''

    # We expect at most one result in the list
    deployment_id = response['deployments'][0]['deploymentId']

    try:
        response = greengrass_client.get_deployment(deploymentId=deployment_id)

        if 'deploymentName' in response:
            print('Found existing named deployment "{}"'.format(response['deploymentName']))
        else:
            print('Found existing unnamed deployment {}'.format(deployment_id))
    except Exception as e:
        print('Failed to get deployment\nException: {}'.format(e))
        response = ''

    return response

def update_deployment(deployment):
    """ Updates the current deplyoment with the desired versions of the components """

    # deployment doesn't exist, so we return and abort
    if deployment == '':
        return

    # Add or update our components to the specified version
    version = get_newest_component_version(detector_venv_component_name)
    if detector_venv_component_name not in deployment['components']:
        print('Adding {} {} to the deployment'.format(detector_venv_component_name, version))
    else:
        print('Updating deployment with {} {}'.format(detector_venv_component_name, version))
    deployment['components'].update({detector_venv_component_name: {'componentVersion': version}})

    version = get_newest_component_version(model_component_name)
    if model_component_name not in deployment['components']:
        print('Adding {} {} to the deployment'.format(model_component_name, version))
    else:
        print('Updating deployment with {} {}'.format(model_component_name, version))
    deployment['components'].update({model_component_name: {'componentVersion': version}})

    version = get_newest_component_version(detector_component_name)
    if detector_component_name not in deployment['components']:
        print('Adding {} {} to the deployment'.format(detector_component_name, version))
    else:
        print('Updating deployment with {} {}'.format(detector_component_name, version))
    deployment['components'].update({detector_component_name: {'componentVersion': version}})

def create_deployment(deployment):
    """ Creates a deployment of the component to the given thing group """

    if deployment == '':
        return ''
    # deployment already exists and was updated, creating 
    # Give the deployment a name if it doesn't already have one
    if 'deploymentName' in deployment:
        deployment_name = deployment['deploymentName']
    else:
        deployment_name = 'Deployment for {}'.format(thing_group_name)
        print('Renaming deployment to "{}"'.format(deployment_name))

    try:
        # We deploy to a single Thing and hence without an IoT job configuration
        # Deploy with default deployment policies and no tags
        response = greengrass_client.create_deployment(
            targetArn=deployment['targetArn'],
            deploymentName=deployment_name,
            components=deployment['components']
        )
    except Exception as e:
        print('Failed to create deployment\nException: {}'.format(e))
        return ''

    return response['deploymentId']

def handler(event, context):
    print(event)
    # grab information about the new deployment package ready for use
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    thing_group_arn = iot_job_client.describe_thing_group(thingGroupName=thing_group_name)['thingGroupArn']

    # Get the latest deployment for the specified thing group
    current_deployment = get_deployment(thing_group_arn)

    # Update the components of the current deployment
    update_deployment(current_deployment)

    # Create a new deployment
    new_deployment_id = create_deployment(current_deployment)
    if new_deployment_id != '':
        print('Deployment {} successfully created. Waiting for completion ...'.format(new_deployment_id))
    else:
        print("Failed to create deployment, aborting")