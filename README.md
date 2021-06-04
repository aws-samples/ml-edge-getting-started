## ML@Edge with SageMaker - Getting Started Examples


This repository contains examples of different models, showing how they can be built using SageMaker and prepared for deployment at the edge.      



In this repository, we will use [Amazon Sagemaker](https://docs.aws.amazon.com/sagemaker/latest/dg/whatis.html) to train the models, [Sagemker-Neo](https://docs.aws.amazon.com/sagemaker/latest/dg/neo.html) to compile them [Sagemaker Edge Manager](https://docs.aws.amazon.com/sagemaker/latest/dg/edge.html) to packaged them. Once the package is created, it can be deployed at the edge devices(for example: Jetson Xavier Jetpack 4.4.1)


Let us understand the structure of the repository:    
- [models](models) folder contains one sub-folder per model/framework type. These subfolders contain a jupyter notebook which does the following:
    - Download the model from the official repository
    - Train the model on a sample dataset
    - Compile the model for an edge device(in this case, a Jetson Xavier Jetpack 4.4.1)
    - Create a SageMaker Edge Manager Packaging job to prepare the deployment package


- [sagemaker_edge_manager_agent_docker](sagemaker_edge_manager_agent_docker) folder contains the details on how to build a docker container for SageMaker Edge Agent.




Below is the list of models with their destination hardware platform, processor and other details.


| Board           | Model                                                         |Processor    | Cold start (no TRT cache) | Cold start time (TRT cache)     | Inference time  |
| -               | -                                                             | -           | -               | -                   | -                   |
| Jetson Nano     | [Tiny Yolov4 416x416 80 classes](models/02_YoloV4/01_Pytorch) |GPU          | ~98.02s         | -             | ~73ms               |
| Jetson Nano     | [Tiny Yolov4 416x416 80 classes](models/02_YoloV4/01_Pytorch) |CPU          | ~0.86s          | -              | ~1503ms             |
| Jetson Xavier   | [Tiny Yolov4 416x416 80 classes](models/02_YoloV4/01_Pytorch) |GPU          | x               | -                   | x               |
| Jetson Xavier   | [Tiny Yolov4 416x416 80 classes](models/02_YoloV4/01_Pytorch) |CPU          | x               | -                   | x               |





## SageMaker Edge Manager Docker container
[Instructions](sagemaker_edge_manager_agent_docker/README.md) of how to create a docker container for the ARM64 agent + Nvidia devices -> Nano/Xavier.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
