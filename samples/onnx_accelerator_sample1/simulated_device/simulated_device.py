#!/usr/bin/python3
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
import logging
import os
import requests
import argparse
import gzip
import paho.mqtt.client as mqtt
import time
import io

BROKER = 'localhost'
PORT = 1883
TOPIC = "turbine/raw"
CLIENT_ID = "turbine_simulated_device"
FILENAME = 'dataset_wind.csv'
DATASET_FILE_URL = 'https://aws-ml-blog.s3.amazonaws.com/artifacts/monitor-manage-anomaly-detection-model-wind-turbine-fleet-sagemaker-neo/dataset_wind_turbine.csv.gz'

class SensorDataReader(object):
            def __init__(self):
                self.buffer = open(FILENAME, 'r').readlines()[1:] # skip the file header
                self.idx = 0
            def isOpen(self): return True
            def close(self): pass
            def readline(self):
                if self.idx >= len(self.buffer): self.idx = 0
                reading = self.buffer[self.idx].strip().split(',')[2:] # drop the first two columns
                reading = reading[0:2] + [reading[3], reading[-1]] + reading[4:-1] # reorganize the columns
                reading = ",".join(reading).encode('utf-8')
                self.idx += 1
                return reading

def download(url, filename):
    try:
        req = requests.get(url)
        with gzip.GzipFile(fileobj=io.BytesIO(req.content), mode="r:gz") as f:
            with open(filename, 'w') as d: d.write(f.read().decode('utf-8'))
            return True
    except Exception as e:
        logging.error(e)
        return False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker")
        client.connected_flag=True         
    else:
        print("Connection failed")

if __name__ == '__main__':
    
    logging.basicConfig(level=logging.INFO )

    if not os.path.exists(FILENAME):
        logging.info("Input dataset not found, downloading it...")
        if download(DATASET_FILE_URL,FILENAME) == False:
            logging.error("Failed to download dataset file, exiting...")
            exit()
        logging.info("File downloaded")
    else:
        logging.info("Dataset present, loading data")

    logging.info("Connecting to MQTT broker...")
    client = mqtt.Client(CLIENT_ID)
    client.connected_flag=False
    client.on_connect = on_connect
    client.loop_start()
    client.connect(BROKER, PORT)
    while not client.connected_flag: #wait in loop
        print("Waiting to connect")
        time.sleep(1)
    logging.info("Connected")

    raw_sensor_data = SensorDataReader()

    try:
        while True:
            data = raw_sensor_data.readline().decode('utf-8').strip()
            logging.info("publishing raw data to MQTT topic")
            client.publish(TOPIC,data)
            time.sleep(0.5)
    except Exception as e:
        logging.error(e)

    logging.info("Shutting down simulated device")
    client.loop_stop()
    client.disconnect()
  
