## A docker container for SageMaker Edge Agent

Building the Docker image
```bash
cd docker
bash build.sh
```

Now, follow these [instructions](https://docs.aws.amazon.com/sagemaker/latest/dg/edge-getting-started-step4.html) to:
 - create a conf/**config.json** 
 - download the root certificate
 - create and download the IoT certificates

```
├──conf
|  ├── config.json
|  certs
|  ├── root
|  |     └──us-west-2.pem
|  ├── iot
|  |     ├── AmazonRootCA1.pem
|  |     ├── device.pem.crt
|  |     └── private.pem.key
|  models
|  ├── modelA/artifacts
|  ├── modelB/artifacts
|  └── modelC/artifacts

```
Running the container on an NVIDIA GPU based instance
```bash
bash run_agent.sh
```
