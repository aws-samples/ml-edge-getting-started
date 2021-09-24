// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Quick and dirty DLR wrapper. Do not use it in production!

#ifndef DLR_CLIENT_H
#define DLR_CLIENT_H

#include "dlr.h"
#include <cstdint>
#include <stdexcept>
#include <iostream>
#include <vector>
#include <chrono>

class DLRClient {
    private:
        const char* backend_name;
        int num_inputs, num_outputs;
        DLRModelHandle* handle = NULL;
        std::vector<std::string> input_names;
        std::vector<std::vector<int64_t>> input_shapes;
        std::vector<std::vector<int64_t>> output_shapes;
        std::vector<int64_t> input_sizes;
        std::vector<int64_t> output_sizes;

	public:
        enum DEV_TYPE {
            CPU=1,
            GPU=2
        };
        inline DLRClient(const std::string& model_path=".", DEV_TYPE dev_type=CPU, int dev_id=0) : handle(new DLRModelHandle()) {
	        // load the model
	        if (CreateDLRModel(this->handle, model_path.c_str(), dev_type, dev_id)) {
        	    const char* err = DLRGetLastError();
        	    throw std::runtime_error(err);
        	} // if
            // get the bakcend --> tvm
            if (GetDLRBackend(this->handle, &this->backend_name)) {
                const char* err = DLRGetLastError();
                    throw std::runtime_error(err);
            } // if
            // get the number of inputs
            if (GetDLRNumInputs(this->handle, &this->num_inputs)) {
                const char* err = DLRGetLastError();
                    throw std::runtime_error(err);
            } // if
            // get the number of outputs
            if (GetDLRNumOutputs(this->handle, &this->num_outputs)) {
                const char* err = DLRGetLastError();
                    throw std::runtime_error(err);
            } // if
            // get the input names and shapes 
            for (int i=0; i < this->num_inputs; ++i ) {
                const char* input_name;
		        if (GetDLRInputName(handle, i, &input_name)) {
        		    const char* err = DLRGetLastError();
        		    throw std::runtime_error(err);
        		} // if
                this->input_names.push_back(input_name);
                int64_t size;
                int dim;
		        if (GetDLRInputSizeDim(handle, i, &size, &dim)) {
        		    const char* err = DLRGetLastError();
        		    throw std::runtime_error(err);
        		} // if
                std::vector<int64_t> shape(dim);
		        if (GetDLRInputShape(handle, i, &shape[0])) {
        		    const char* err = DLRGetLastError();
        		    throw std::runtime_error(err);
        		} // if
                this->input_shapes.push_back(shape);
                this->input_sizes.push_back(size);
            } // for
            // get the output shapes
            for (int i=0; i < this->num_outputs; ++i ) {
                int64_t size;
                int dim;
                if (GetDLROutputSizeDim(this->handle, i, &size, &dim)) {
                    const char* err = DLRGetLastError();
                        throw std::runtime_error(err);
                } // if
                std::vector<int64_t> shape(dim);
		        if (GetDLROutputShape(handle, i, &shape[0])) {
        		    const char* err = DLRGetLastError();
        		    throw std::runtime_error(err);
        		} // if
                this->output_shapes.push_back(shape);
                this->output_sizes.push_back(size);
            } // for
        }

        inline void run_inference(const std::vector<std::vector<float>>& input, std::vector<std::vector<float>>& output) {
            if (output.size() != 0 ) {
                throw std::runtime_error("You need to provide an empty output vector");
            } // if
            if (this->num_inputs != input.size()) {
                throw std::runtime_error("Invalid input elements. Expected: " + std::to_string(this->num_inputs) + " Received: " + std::to_string(input.size()));
            } // if
            for ( int i=0; i < this->num_inputs; ++i ) {
                const std::vector<int64_t>& shape = this->input_shapes[i];
            	if (SetDLRInput(handle, this->input_names[i].c_str(), shape.data(), input[i].data(), shape.size()) != 0) {
            		const char* err = DLRGetLastError();
            	 	throw std::runtime_error(err);
            	} // if
            } // for
        	if (RunDLRModel(handle) != 0) {
        		const char* err = DLRGetLastError();
        	 	throw std::runtime_error(err);
        	} // if
            for ( int i=0; i < this->num_outputs; ++i ) {
                std::vector<float> buf;
                output.push_back(buf);
                output[i].resize(this->output_sizes[i], 0);
            	if (GetDLROutput(handle, i, output[i].data()) != 0) {
            		const char* err = DLRGetLastError();
            	 	throw std::runtime_error(err);
            	} // if
            } // for
        }

        inline const std::vector<int64_t>& get_input_sizes(void) const {
            return this->input_sizes;
        }
        inline const std::vector<int64_t>& get_output_sizes(void) const {
            return this->output_sizes;
        }
        inline const std::vector<std::vector<int64_t>>& get_input_shapes(void) const {
            return this->input_shapes;
        }
        inline const std::vector<std::vector<int64_t>>& get_output_shapes(void) const {
            return this->output_shapes;
        }
   
        virtual inline ~DLRClient(void) {
            if ( this->handle != NULL ) {
                DeleteDLRModel(this->handle);
            } // if
        }
};

#endif // DLR_CLIENT_H
