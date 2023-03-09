# Edge application

This is a Python application that runs on the Edge device. It connects all the components together and is reponsible for the loop that reads the sensors data, prepare the data, invoke the ML model and report back to the cloud.

## Pre-requisites

- Raspberry pi configured with Python 3.9 and pip3
- 64 bit OS (tested with Raspbian 64 bit, see [here](https://www.raspberrypi.com/software/operating-systems/) for additional information)
- Simulated device correctly configured and running

## Getting started

### Provision your device

We provide instructions to run in command line using the AWS console. You can also perform the same actions from the CLI.

- Create a thing type

In the console, go to IoT Core -> All devices -> Thing types -> Create thing type
In the wizard, name it ```WindTurbines``` and click create thing type.

- Create a thing group

In the console, go to IoT Core -> All devices -> Thing groups -> Create thing group
In the wizard, select Create static thing group -> name it ```WindTurbines``` and click create thing group.

- Create a thing group policy

In IoT Core, go to Security -> Policies and create a new policy named ```WindTurbines_group_policy``` and copy paste the following JSON by replacing the values of ```REGION``` and ```ACCOUNT``` with your current region and AWS account id:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/device/${iot:ClientId}/logs",
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/$aws/events/job/*",
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/$aws/events/jobExecution/*",
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/$aws/things/${iot:ClientId}/jobs/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:REGION:ACCOUNT_ID:client/${iot:ClientId}"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Subscribe",
      "Resource": [
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/$aws/events/jobExecution/*",
        "arn:aws:iot:REGION:ACCOUNT_ID:topicfilter/$aws/things/${iot:ClientId}/jobs/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:Receive"
      ],
      "Resource": [
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/$aws/things/${iot:ClientId}/jobs/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:DescribeJobExecution",
        "iot:GetPendingJobExecutions",
        "iot:StartNextPendingJobExecution",
        "iot:UpdateJobExecution"
      ],
      "Resource": [
        "arn:aws:iot:REGION:ACCOUNT_ID:topic/$aws/things/${iot:ClientId}"
      ]
    }
  ]
}
```

- Attach thing group policy to thing group

In IoT Core, select Things groups -> WindTurbines -> Policies tab and click on manage policies. Then select the ```WindTurbines_group_policy``` and validate
 
- Creating a Thing and certificates

In the console, go to IoT Core -> All devices -> Things -> Create thing

In the wizard, select "Create a single thing". For the name, use ```WindTurbineOne```. For the thing type, select ```WindTurbines```. For the thing group, select ```WindTurbines```. Click Next.

Select "Auto-generate a new certificate". Don't select any policy to attach to the certificate. You can authorise devices by attaching an IoT policy to a thing group instead of a device certificate. The policy attached to the thing group we created earlier uses policy variables so that a device is only allowed to publish to the topic.
On the new pop window, download the device certificate, private key and amazon root CA and store them in a new folder called ```certs```. This is the only time you can download the key files for this certificate.

- Get the IoT data endpoint

In IoT Core, select Settings and copy the value of ```Device data endpoint```. The value should look like this: ```xxxxxxx-ats.iot.REGION.amazonaws.com```


### Prepare edge device

- If not done previously, copy the device certificates to this folder, under certs. Rename the certificates to match the following structure:
```
edge_application
  | statistics/
  | turbine/
  | certs/
    | private.pem
    | certificate.pem
    | amznrootca.pem
  | config.json
  | edge_application.py
  | requirements.txt
  | README.md
```

- Replace the value of ```target_endpoint``` in config.json by the value of the iot endpoint you pulled earlier (```Device data endpoint```)

- Copy the content of this folder to your Raspberry Pi. For instance, from your local machine:
    ```shell
    $ rsync -a . username@host:/home/username/edge_application
    ```
    by replacing ***username*** and ***host*** with your Raspberry Pi information

On your Raspberry Pi:

- Go to the folder previously copied and install the dependencies:
    ```shell
    $ cd /home/username/edge_application && pip3 install -r requirements.txt
    ```

- You might need to install the following package: ```sudo apt-get install libatlas-base-dev```

- Your application should be ready now ! Execute it to test:

  ```
    python3 edge_application.py
  ```