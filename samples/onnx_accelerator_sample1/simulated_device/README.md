# Simulated device

This Python application simulates a wind turbine device and streams raw data over mqtt on a specified topic. Data are downloaded from this sample dataset: ```https://aws-ml-blog.s3.amazonaws.com/artifacts/monitor-manage-anomaly-detection-model-wind-turbine-fleet-sagemaker-neo/dataset_wind_turbine.csv.gz```

The data has the following features:

- nanoId – ID of the edge device that collected the data
- turbineId – ID of the turbine that produced this data
- arduino_timestamp – Timestamp of the Arduino that was operating this turbine
- nanoFreemem: Amount of free memory in bytes
- eventTime – Timestamp of the row
- rps – Rotation of the rotor in rotations per second
- voltage – Voltage produced by the generator in milivolts
- qw, qx, qy, qz – Quaternion angular acceleration
- gx, gy, gz – Gravity acceleration
- ax, ay, az – Linear acceleration
- gearboxtemp – Internal temperature
- ambtemp – External temperature
- humidity – Air humidity
- pressure – Air pressure
- gas – Air quality
- wind_speed_rps – Wind speed in rotations per second

Additional information on the wind turbine can be found [here](https://aws.amazon.com/blogs/machine-learning/monitor-and-manage-anomaly-detection-models-on-a-fleet-of-wind-turbines-with-amazon-sagemaker-edge-manager/)

## Pre-requisites

- Raspberry pi configured with Python 3.9 and pip3
- 64 bit OS (tested with Raspbian 64 bit, see [here](https://www.raspberrypi.com/software/operating-systems/) for additional information)

## Getting started

- Copy the content of this folder to your Raspberry Pi. For instance, from your local machine:
    ```shell
    $ rsync -a . username@host:/home/username/simulated_device
    ```
    by replacing ***username*** and ***host*** with your Raspberry Pi information

On your Raspberry Pi:

- Install mosquitto as an MQTT broker and related clients: 
    ```shell
    $ sudo apt-get install mosquitto && sudo apt-get install mosquitto-clients
    ```
This will be used to test that the application is correctly running
- Go to the folder previously copied and install the dependencies:
    ```shell
    $ cd /home/username/simulated_device && pip3 install -r requirements.txt
    ```
- Run the application: 
    ```shell
    $ python3 simulated_device.py
    ```
- Open a second terminal on your Rpi and verify that your data are available: 
    ```shell
    $ mosquitto-sub -d -t turbine/raw
    ```


