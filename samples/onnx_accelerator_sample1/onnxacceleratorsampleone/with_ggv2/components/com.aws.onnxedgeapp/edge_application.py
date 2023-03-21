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
import argparse
import logging
import time
import paho.mqtt.client as mqtt
import json
import numpy as np
import turbine
from queue import Queue
import onnxruntime as ort
from datetime import datetime
import sys
import os

# buffer size required to process timeseries data
PREDICTIONS_INTERVAL = 1.0 # interval in seconds between the predictions
MIN_NUM_SAMPLES = 500         
INTERVAL = 5 # seconds
TIME_STEPS = 20 * INTERVAL
STEP = 10
FEATURES_IDX = [6,7,8,5,  3, 2, 4] # qX,qy,qz,qw  ,wind_seed_rps, rps, voltage 
NUM_RAW_FEATURES = 20
NUM_FEATURES = 6

connected = False

q=Queue()
tokens_q = Queue()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker for raw data acquisition")
        client.connected_flag=True
        client.subscribe('turbine/raw')         
    else:
        print("Connection failed")

def on_message(client, userdata, msg):
    data = msg.payload.decode('utf8')
    try:
        tokens = np.array(data.split(','))
        # check if the format is correct
        if len(tokens) != NUM_RAW_FEATURES:
            print(data)
            logging.error('Wrong # of features. Expected: %d, Got: %d' % ( NUM_RAW_FEATURES, len(tokens)))
            return
        # add noise to raw data randomly
        if np.random.randint(50) == 0:
            print("adding noise to radians")
            tokens[FEATURES_IDX[0:4]] = np.random.rand(4) * 10 # out of the radians range
        if np.random.randint(20) == 0:
            print("adding noise to wind")
            tokens[FEATURES_IDX[5]] = np.random.rand(1)[0] * 10 # out of the normalized wind range
        if np.random.randint(50) == 0:
            print("adding noise to voltage")
            tokens[FEATURES_IDX[6]] = int(np.random.rand(1)[0] * 1000) # out of the normalized voltage range
    except Exception as e:
        logging.error(e)
        logging.error(data)
    ts = "%s+00:00" % datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    tokens_q.put({'ts': ts, 'values': tokens.tolist()})
    # get only the used features
    data = [float(tokens[i]) for i in FEATURES_IDX]
    # compute the euler angles from the quaternion
    roll,pitch,yaw = turbine.euler_from_quaternion(data[0],data[1],data[2],data[3])
    data = np.array([roll,pitch,yaw, data[4], data[5], data[6]])
    #logging.info("Adding data to samples: %s", data)
    q.put(data)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO )

    # load the json configuration
    parser = argparse.ArgumentParser()    
    print("[Main] Arguments - ", sys.argv[1:])
    parser.add_argument("--config", type=str,required = True)
    args = parser.parse_args()
    print("[Main] ConfigRaw - ", args.config)        
    config = json.loads(args.config)
    print("[Main] ConfigJson - ", config) 

    # Connect to the broker to acquire simulated data
    logging.info("Connecting to MQTT broker...")
    client = mqtt.Client('onnx_edge_app')
    client.connected_flag=False
    client.on_connect = on_connect
    client.on_message = on_message
    client.loop_start()
    client.connect(config['broker'], config['port'])
    while not client.connected_flag: #wait in loop
        print("Waiting to connect")
        time.sleep(1)
    logging.info("Connected")

    # Initialize the OTA Model Manager
    model_name = config['model_name']
    model_version = config['model_version']

    # load model -> since the artifact is an archive, we create in the recipe an env
    # variable containing the decompressed path to the model
    sess = ort.InferenceSession(os.environ['ONNX_MODEL_PATH'])

    cloud_connector = turbine.CloudConnector()
    
    # Some constants used for data prep + compare the results
    statistics_path = os.environ['STATISTICS_PATH']
    thresholds = np.load(statistics_path+'thresholds.npy')
    raw_std = np.load(statistics_path+'raw_std.npy')
    mean = np.load(statistics_path+'mean.npy')
    std = np.load(statistics_path+'std.npy')
    
    try:
        while True:
            cloud_connector.publish_logs(tokens_q.get())

            if q.qsize() <= MIN_NUM_SAMPLES:
                if q.qsize() % 10 == 0:
                    logging.info('Buffering %d/%d... please wait' % (q.qsize(), MIN_NUM_SAMPLES))
                    time.sleep(1)
                # buffering
                continue

            # prep the data for the model
            li = list(q.queue)
            data = np.array(li) # create a copy
            q.get() # remove the oldest sample            
            data = np.array([turbine.wavelet_denoise(data[:,i], raw_std[i], 'db6') for i in range(NUM_FEATURES)])
            data = data.transpose((1,0))
            data -= mean
            data /= std
            data = data[-(TIME_STEPS+STEP):]

            x = turbine.create_dataset(data, TIME_STEPS, STEP)
            x = np.transpose(x, (0, 2, 1)).reshape(x.shape[0], NUM_FEATURES, 10, 10).astype(np.float32)

            # Now we can run our model using the loaded data
            # The run command lets you specify which outputs you want to get returned. it only has one output.
            ptemp = sess.run(None, {"input": x})

            # We are converting the prediction output to a numpy array so that we can convert it into
            # something human readable
            p = np.asarray(ptemp[0])

            a = x.reshape(x.shape[0], NUM_FEATURES, 100).transpose((0,2,1))
            b = p.reshape(p.shape[0], NUM_FEATURES, 100).transpose((0,2,1))
            
            # check the anomalies
            pred_mae_loss = np.mean(np.abs(b - a), axis=1).transpose((1,0))
            values = np.mean(pred_mae_loss, axis=1)
            anomalies = (values > thresholds)
            
            # publish data to visualize in dashboard
            ts = "%s+00:00" % datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            cloud_connector.publish_inference(anomalies.astype(np.float32), values.astype(np.float32), model_name, model_version, ts)

            if anomalies.any():
                logging.info("Anomaly detected: %s" % anomalies)
            else:
                logging.info("Ok")

            time.sleep(PREDICTIONS_INTERVAL)
    except KeyboardInterrupt as e:
        pass
    except Exception as e:
        logging.error(e)

    logging.info("Shutting down")
    client.loop_stop()
    client.disconnect()
    cloud_connector.exit("Done")








