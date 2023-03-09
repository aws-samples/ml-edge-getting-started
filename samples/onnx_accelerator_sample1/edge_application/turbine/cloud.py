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

from awscrt import mqtt
from awsiot import iotjobs, mqtt_connection_builder
from concurrent.futures import Future
import sys
import threading
import time
import traceback
import time
import requests
from uuid import uuid4
import json

class LockedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.disconnect_called = False
        self.is_working_on_job = False
        self.is_next_job_waiting = False
        self.got_job_response = False

class CloudConnector(object):
    def __init__(self, iot_params, starting_model_update_callback, update_callback, model_path):
        proxy_options = None

        self.locked_data = LockedData()
        self.update_callback = update_callback
        self.starting_model_update_callback = starting_model_update_callback
        self.model_name = None
        self.model_version = None
        self.mqtt_connection = None
        self.jobs_client = None
        # A list to hold all the pending jobs
        self.available_jobs = []

        self.thing_name = iot_params['thing_name']

        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=iot_params['target_endpoint'],
            port=8883,
            cert_filepath=iot_params['cert_filepath'],
            pri_key_filepath=iot_params['private_key_filepath'],
            ca_filepath=iot_params['ca_filepath'],
            on_connection_interrupted=None,
            on_connection_resumed=None,
            client_id=self.thing_name,
            clean_session=True,
            keep_alive_secs=30,
            http_proxy_options=proxy_options)

        connected_future = self.mqtt_connection.connect()

        self.jobs_client = iotjobs.IotJobsClient(self.mqtt_connection)

        # Wait for connection to be fully established.
        # Note that it's not necessary to wait, commands issued to the
        # mqtt_connection before its fully connected will simply be queued.
        # But this sample waits here so it's obvious when a connection
        # fails or succeeds.
        connected_future.result()
        print("Connected to the cloud")

        try:
            # List the jobs queued and pending
            get_jobs_request = iotjobs.GetPendingJobExecutionsRequest(thing_name=self.thing_name)
            jobs_request_future_accepted, _ = self.jobs_client.subscribe_to_get_pending_job_executions_accepted(
                request=get_jobs_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_get_pending_job_executions_accepted
            )
            # Wait for the subscription to succeed
            jobs_request_future_accepted.result()

            jobs_request_future_rejected, _ = self.jobs_client.subscribe_to_get_pending_job_executions_rejected(
                request=get_jobs_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_get_pending_job_executions_rejected
            )
            # Wait for the subscription to succeed
            jobs_request_future_rejected.result()

            # Get a list of all the jobs
            get_jobs_request_future = self.jobs_client.publish_get_pending_job_executions(
                request=get_jobs_request,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
            # Wait for the publish to succeed
            get_jobs_request_future.result()
        except Exception as e:
            self.exit(e)

        try:
            # Subscribe to necessary topics.
            # Note that is **is** important to wait for "accepted/rejected" subscriptions
            # to succeed before publishing the corresponding "request".
            print("Subscribing to Next Changed events...")
            changed_subscription_request = iotjobs.NextJobExecutionChangedSubscriptionRequest(
                thing_name=self.thing_name)

            subscribed_future, _ = self.jobs_client.subscribe_to_next_job_execution_changed_events(
                request=changed_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_next_job_execution_changed)

            # Wait for subscription to succeed
            subscribed_future.result()

            print("Subscribing to Start responses...")
            start_subscription_request = iotjobs.StartNextPendingJobExecutionSubscriptionRequest(
                thing_name=self.thing_name)
            subscribed_accepted_future, _ = self.jobs_client.subscribe_to_start_next_pending_job_execution_accepted(
                request=start_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_start_next_pending_job_execution_accepted)

            subscribed_rejected_future, _ = self.jobs_client.subscribe_to_start_next_pending_job_execution_rejected(
                request=start_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_start_next_pending_job_execution_rejected)

            # Wait for subscriptions to succeed
            subscribed_accepted_future.result()
            subscribed_rejected_future.result()

            print("Subscribing to Update responses...")
            # Note that we subscribe to "+", the MQTT wildcard, to receive
            # responses about any job-ID.
            update_subscription_request = iotjobs.UpdateJobExecutionSubscriptionRequest(
                    thing_name=self.thing_name,
                    job_id='+')

            subscribed_accepted_future, _ = self.jobs_client.subscribe_to_update_job_execution_accepted(
                request=update_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_update_job_execution_accepted)

            subscribed_rejected_future, _ = self.jobs_client.subscribe_to_update_job_execution_rejected(
                request=update_subscription_request,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=self.on_update_job_execution_rejected)

            # Wait for subscriptions to succeed
            subscribed_accepted_future.result()
            subscribed_rejected_future.result()

            # Make initial attempt to start next job. The service should reply with
            # an "accepted" response, even if no jobs are pending. The response
            # will contain data about the next job, if there is one.
            # (Will do nothing if we are in CI)
            self.try_start_next_job()

        except Exception as e:
            self.exit(e)

    # Function for gracefully quitting this sample
    def exit(self, msg_or_exception):
        if isinstance(msg_or_exception, Exception):
            print("Exiting app due to exception.")
            traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
        else:
            print("Exiting app:", msg_or_exception)

        with self.locked_data.lock:
            if not self.locked_data.disconnect_called:
                print("Disconnecting...")
                self.locked_data.disconnect_called = True
                future = self.mqtt_connection.disconnect()
                future.add_done_callback(self.on_disconnected)

    def try_start_next_job(self):
        print("Trying to start the next job...")
        with self.locked_data.lock:
            if self.locked_data.is_working_on_job:
                print("Nevermind, already working on a job.")
                return

            if self.locked_data.disconnect_called:
                print("Nevermind, sample is disconnecting.")
                return

            self.locked_data.is_working_on_job = True
            self.locked_data.is_next_job_waiting = False

        print("Publishing request to start next job...")
        request = iotjobs.StartNextPendingJobExecutionRequest(thing_name=self.thing_name)
        publish_future = self.jobs_client.publish_start_next_pending_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
        publish_future.add_done_callback(self.on_publish_start_next_pending_job_execution)

    def done_working_on_job(self):
        with self.locked_data.lock:
            self.locked_data.is_working_on_job = False
            try_again = self.locked_data.is_next_job_waiting

        if try_again:
            self.try_start_next_job()

    def on_disconnected(self, disconnect_future):
        # type: (Future) -> None
        print("Disconnected.")

    def on_get_pending_job_executions_accepted(self, response):
        # type: (iotjobs.GetPendingJobExecutionsResponse) -> None
        with self.locked_data.lock:
            if (len(response.queued_jobs) > 0 or len(response.in_progress_jobs) > 0):
                print ("Pending Jobs:")
                for job in response.in_progress_jobs:
                    self.available_jobs.append(job)
                    print(f"  In Progress: {job.job_id} @ {job.last_updated_at}")
                for job in response.queued_jobs:
                    self.available_jobs.append(job)
                    print (f"  {job.job_id} @ {job.last_updated_at}")
            else:
                print ("No pending or queued jobs found!")
            self.locked_data.got_job_response = True

    def on_get_pending_job_executions_rejected(self, error):
        # type: (iotjobs.RejectedError) -> None
        print (f"Request rejected: {error.code}: {error.message}")
        exit("Get pending jobs request rejected!")


    def on_next_job_execution_changed(self, event):
        # type: (iotjobs.NextJobExecutionChangedEvent) -> None
        try:
            execution = event.execution
            if execution:
                print("Received Next Job Execution Changed event. job_id:{} job_document:{}".format(
                    execution.job_id, execution.job_document))

                # Start job now, or remember to start it when current job is done
                start_job_now = False
                with self.locked_data.lock:
                    if self.locked_data.is_working_on_job:
                        self.locked_data.is_next_job_waiting = True
                    else:
                        start_job_now = True

                if start_job_now:
                    self.try_start_next_job()

            else:
                print("Received Next Job Execution Changed event: None. Waiting for further jobs...")

        except Exception as e:
            self.exit(e)

    def on_publish_start_next_pending_job_execution(self, future):
        # type: (Future) -> None
        try:
            future.result() # raises exception if publish failed

            print("Published request to start the next job.")

        except Exception as e:
            self.exit(e)

    def on_start_next_pending_job_execution_accepted(self, response):
        # type: (iotjobs.StartNextJobExecutionResponse) -> None
        try:
            if response.execution:
                execution = response.execution
                print("Request to start next job was accepted. job_id:{} job_document:{}".format(
                    execution.job_id, execution.job_document))

                job_thread = threading.Thread(
                    target=lambda: self.job_thread_fn(execution.job_id, execution.job_document),
                    name='job_thread')
                job_thread.start()
            else:
                print("Request to start next job was accepted, but there are no jobs to be done. Waiting for further jobs...")
                self.done_working_on_job()

        except Exception as e:
            self.exit(e)

    def on_start_next_pending_job_execution_rejected(self, rejected):
        # type: (iotjobs.RejectedError) -> None
        self.exit("Request to start next pending job rejected with code:'{}' message:'{}'".format(
            rejected.code, rejected.message))

    def job_thread_fn(self, job_id, job_document):
        try:
            print("Starting local work on job...")

            #let know the app that a model udpate is happening
            self.starting_model_update_callback()

            '''
                This method is responsible for:
                    1. validate the new model version
                    2. download the model package
                    3. unpack it to a local dir
                    4. notify the main application
            '''
            print("Validating job document")
            if job_document['operation'] == 'update_model' and job_document['version'] == '1.0.0':                
                model_version = job_document['model_version']
                model_name = job_document['model_name']
            else:
                print("Operation type and/or job version not supported")
                self.update_callback(self.model_name, self.model_version)
                request = iotjobs.UpdateJobExecutionRequest(
                thing_name=self.thing_name,
                job_id=job_id,
                status=iotjobs.JobStatus.FAILED)
                publish_future = self.jobs_client.publish_update_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
                publish_future.add_done_callback(self.on_publish_update_job_execution)
                return

            if model_version is not None and self.model_version is not None:
                if model_version <= self.model_version:
                    print("New model version is not newer than the current one. Curr: %f; New: %f;" % (self.model_version, model_version))
                    self.update_callback(self.model_name, self.model_version)
                    request = iotjobs.UpdateJobExecutionRequest(
                    thing_name=self.thing_name,
                    job_id=job_id,
                    status=iotjobs.JobStatus.FAILED)
                    publish_future = self.jobs_client.publish_update_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
                    publish_future.add_done_callback(self.on_publish_update_job_execution)
                    return

            deployment_package_path = job_document['deployment_artifact_path']

            # download artifacts
            print("Downloading new model...")
            r = requests.get(deployment_package_path)
            with open ('/home/awsab3ak/edge_application/'+model_name+'.onnx', 'wb') as f:
                f.write(r.content)
            
            self.model_version = model_version
            self.model_name = model_name

            print("Done working on job.")
            self.update_callback(self.model_name, self.model_version) 

            print("Publishing request to update job status to SUCCEEDED...")
            request = iotjobs.UpdateJobExecutionRequest(
                thing_name=self.thing_name,
                job_id=job_id,
                status=iotjobs.JobStatus.SUCCEEDED)
            publish_future = self.jobs_client.publish_update_job_execution(request, mqtt.QoS.AT_LEAST_ONCE)
            publish_future.add_done_callback(self.on_publish_update_job_execution)

        except Exception as e:
            self.exit(e)

    def on_publish_update_job_execution(self, future):
        # type: (Future) -> None
        try:
            future.result() # raises exception if publish failed
            print("Published request to update job.")

        except Exception as e:
            self.exit(e)

    def on_update_job_execution_accepted(self, response):
        # type: (iotjobs.UpdateJobExecutionResponse) -> None
        try:
            print("Request to update job was accepted.")
            self.done_working_on_job()
        except Exception as e:
            self.exit(e)

    def publish_inference(self, anomalies, values, model_name, model_version, ts):
        try:
            dictionary = {
                "type": "inference",
                "model_name": model_name,
                "model_version": model_version,
                "anomalies": anomalies.tolist(),
                "values": values.tolist(),
                "ts": ts
            }
            message_json = json.dumps(dictionary)
            self.mqtt_connection.publish(
                topic='device/'+self.thing_name+'/logs',
                payload=message_json,
                qos=mqtt.QoS.AT_LEAST_ONCE)
        except Exception as e:
            print(e)

    def publish_logs(self, data):
        try:
            dictionary = {
                "type": "rawdata",
                "data": data
            }
            message_json = json.dumps(dictionary)
            self.mqtt_connection.publish(
                topic='device/'+self.thing_name+'/logs',
                payload=message_json,
                qos=mqtt.QoS.AT_LEAST_ONCE)
        except Exception as e:
            print(e)

    def on_update_job_execution_rejected(self, rejected):
        # type: (iotjobs.RejectedError) -> None
        self.exit("Request to update job status was rejected. code:'{}' message:'{}'.".format(
            rejected.code, rejected.message))
        
