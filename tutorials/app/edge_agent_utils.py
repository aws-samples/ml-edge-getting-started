# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import agent_pb2 as agent
import agent_pb2_grpc as agent_grpc
import numpy as np

def list_models(cli):
    resp = cli.ListModels(agent.ListModelsRequest())
    return {m.name:{'in': m.input_tensor_metadatas, 'out': m.output_tensor_metadatas} for m in resp.models}

def load_model(cli, model_name, model_path):
    """ Load a new model into the Edge Agent if not loaded yet"""
    try:
        req = agent.LoadModelRequest()
        req.url = model_path
        req.name = model_name
        return cli.LoadModel(req)        
    except Exception as e:
        print(e)        
        return None

def unload_model(cli, model_name):
    """ UnLoad model from the Edge Agent"""
    try:
        req = agent.UnLoadModelRequest()
        req.name = model_name
        resp = cli.UnLoadModel(req)
        return resp
    except Exception as e:
        print(e)
        return None

def predict(cli, model_name, x, shm=False):
    """
    Invokes the model and get the predictions
    """
    try:
        model_map = list_models(cli)
        if model_map.get(model_name) is None:
            raise Exception('Model %s not loaded' % model_name)
        # Create a request
        req = agent.PredictRequest()
        req.name = model_name
        # Then load the data into a temp Tensor
        tensor = agent.Tensor()
        meta = model_map[model_name]['in'][0]
        tensor.tensor_metadata.name = meta.name
        tensor.tensor_metadata.data_type = meta.data_type
        for s in meta.shape: tensor.tensor_metadata.shape.append(s)
        
        if shm:
            tensor.shared_memory_handle.offset = 0
            tensor.shared_memory_handle.segment_id = x
        else:
            tensor.byte_data = x.astype(np.float32).tobytes()

        req.tensors.append(tensor)

        # Invoke the model
        resp = cli.Predict(req)

        # Parse the output
        meta = model_map[model_name]['out'][0]
        tensor = resp.tensors[0]
        data = np.frombuffer(tensor.byte_data, dtype=np.float32)
        return data.reshape(tensor.tensor_metadata.shape)
    except Exception as e:
        print(e)        
        return None

def create_tensor(x, tensor_name):
    if (x.dtype != np.float32):
        raise Exception( "It only supports numpy float32 arrays for this tensor" )    
    tensor = agent.Tensor()    
    tensor.tensor_metadata.name = tensor_name.encode('utf-8')
    tensor.tensor_metadata.data_type = agent.FLOAT32
    for s in x.shape: tensor.tensor_metadata.shape.append(s)
    tensor.byte_data = x.tobytes()
    return tensor

def capture_data(cli, model_name, input_tensor, output_tensor):
    try:
        req = agent.CaptureDataRequest()
        req.model_name = model_name
        req.capture_id = str(uuid.uuid4())
        req.input_tensors.append( create_tensor(input_tensor, 'input') )
        req.output_tensors.append( create_tensor(output_tensor, 'output') )
        resp = cli.CaptureData(req)
    except Exception as e:            
        print(e)

def write_to_shm(sm, payload):
    if sm.attached: sm.detach()
    # set mode read/write
    sm.mode = 0o0600
    sm.attach()
    sm.write(payload.astype(np.float32).tobytes())
    # set mode read only
    sm.mode = 0o0400
