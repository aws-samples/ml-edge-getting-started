// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

#include <iostream>
#include <fstream>
#include <chrono>
#include <tuple>
#include "processor.hpp"
#include "xtensor/xadapt.hpp"
#include "xtensor/xbuilder.hpp"
#include "xtensor/xnpy.hpp"
#include "xtensor/xio.hpp"
#include "dlrclient.hpp"

int main(int argc, char* argv[] ) {
    if (argc != 3) {
        std::cerr << "ERROR: Inform the model dir and the input image" << std::endl;
        std::cerr << "Usage:" << std::endl << argv[0] << " <MODEL_DIR> <RAW_IMAGE_PATH>" << std::endl;
        std::cerr << " --> Use the python script convert_img.py in the source dir to create your RAW_IMAGE file" << std::endl;
        return 1;
    } // if
    std::fstream file(argv[2], std::ios::binary | std::ios::in);
    if (!file.is_open()) {
        std::cerr << "ERROR: Could not open file: argv[2]" << std::endl;
        return 1;
    } // if

    // load the model and get its metadata
    DLRClient dlr(argv[1], DLRClient::CPU); //1=cpu 2=gpu
    const std::vector<int64_t>& input_sizes = dlr.get_input_sizes();
    const std::vector<int64_t>& output_sizes = dlr.get_output_sizes();
    const std::vector<std::vector<int64_t>>& input_shapes = dlr.get_input_shapes();
    const std::vector<std::vector<int64_t>>& output_shapes = dlr.get_output_shapes();
    std::vector<std::vector<float>> input,output;

    // copy the image to the input vector
    for ( int i=0; i < input_sizes.size(); ++i ) {
        std::vector<float> buf;
        input.push_back(buf);
        input[i].resize(input_sizes[i], 0);
        file.read(reinterpret_cast<char*>(input[i].data()), input_sizes[i]*4);
    } // for
    file.close();

    // run the model and get the predictions at output
    auto start = std::chrono::high_resolution_clock::now();
    dlr.run_inference(input, output);
    auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::high_resolution_clock::now() - start);
    std::cout << "Prediction elapsed time: " << (elapsed.count()/1000.0) << "ms" << std::endl;
    // convert the output into xarray and with the expected shape
    std::vector<vecf> pred;
    for ( int i=0; i < output_sizes.size(); ++i ) {
        vecf out;
        pred.push_back(out);
        pred[i] = xt::adapt(output[i], output_shapes[i]);
    } // for

    // post process to get the detections
    start = std::chrono::high_resolution_clock::now();
    std::tuple<vecf, vecf, vecf> detections = Processor::get().detect(pred);
    elapsed = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::high_resolution_clock::now() - start);
    std::cout << "Post-processing - elapsed time: " << (elapsed.count()/1000.0) << "ms" << std::endl;

    // print the results
    vecf& bboxes = std::get<0>(detections);
    vecf& scores = std::get<1>(detections);
    vecf& cids = std::get<2>(detections);
    std::cout << "bboxes (x1y1x2y2 %->input_shape): " << xt::adapt(bboxes.shape()) << std::endl << bboxes << std::endl;
    std::cout << "scores: " << xt::adapt(scores.shape()) << std::endl << scores << std::endl;
    std::cout << "cids: " << xt::adapt(cids.shape()) << std::endl << cids << std::endl;

    return 0;
}
