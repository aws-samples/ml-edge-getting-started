// Original Copyright Microsoft Corporation. Licensed under the MIT License.
// Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import _ from 'lodash';

// 2022-08-19: Amazon addition.
import {Tensor, InferenceSession} from 'onnxruntime-web';

let inferenceSessionWebGl: InferenceSession | null = null;
let inferenceSessionWebAssembly: InferenceSession | null = null;

import { imagesClasses } from '../data/classses';

export async function createInferenceSession(modelFileUrl: any) {
    try {
        inferenceSessionWebAssembly = await InferenceSession
            .create(modelFileUrl, {executionProviders: ['wasm'], graphOptimizationLevel: 'all'});
            console.log("success for wasm");
        } catch (e) {
        inferenceSessionWebAssembly = null;

        console.error('Error creating ONNX WebAssembly InferenceSession', e)
    }

    try {
        inferenceSessionWebGl = await InferenceSession
            .create(modelFileUrl, {executionProviders: ['webgl'], graphOptimizationLevel: 'all'});
            console.log("success for webgl");
    } catch (e) {
        inferenceSessionWebGl = null

        console.error('Error creating ONNX WebGl InferenceSession', e)
    }
}

export async function runModelInference(preprocessedData: any): Promise<any> {
    const [webAssemblyInferenceResponse, webGlInferenceResponse] = await Promise.all([
        runInference(inferenceSessionWebAssembly, preprocessedData),
        runInference(inferenceSessionWebGl, preprocessedData)
    ])

    let inferenceResponse = [
        {
            type: 'WebAssembly',
            response: webAssemblyInferenceResponse
        },
        {
            type: 'WebGL',
            response: webGlInferenceResponse
        },
    ]

    return inferenceResponse;
}

async function runInference(session: any, preprocessedData: any): Promise<[any, number]> {
    if (!session) {
        return [[], 0]
    }
// End of Amazon addition.

    // Get start time to calculate inference time.
    const start = new Date();
    // create feeds with the input name from model export and the preprocessed data.
    const feeds: Record<string, Tensor> = {};
    feeds[session.inputNames[0]] = preprocessedData;

    // Run the session inference.
    const outputData = await session.run(feeds);
    // Get the end time to calculate inference time.
    console.log(outputData);
    const end = new Date();
    // Convert to seconds.
    const inferenceTime = (end.getTime() - start.getTime()) / 1000;
    // Get output results with the output name from the model export.
    const output = outputData[session.outputNames[0]];
    //Get the softmax of the output data. The softmax transforms values to be between 0 and 1
    var outputSoftmax = softmax(Array.prototype.slice.call(output.data));

    //Get the top 5 results.
    var results = imagenetClassesTopK(outputSoftmax, 5);

    console.log('results: ', results);

    return [results, inferenceTime];
}

//The softmax transforms values to be between 0 and 1
function softmax(resultArray: number[]): any {
    // Get the largest value in the array.
    const largestNumber = Math.max(...resultArray);
    // Apply exponential function to each result item subtracted by the largest number, use reduce to get the previous result number and the current number to sum all the exponentials results.
    const sumOfExp = resultArray.map((resultItem) => Math.exp(resultItem - largestNumber)).reduce((prevNumber, currentNumber) => prevNumber + currentNumber);
    //Normalizes the resultArray by dividing by the sum of all exponentials; this normalization ensures that the sum of the components of the output vector is 1.
    return resultArray.map((resultValue, index) => {
        return Math.exp(resultValue - largestNumber) / sumOfExp;
    });
}

/**
 * Find top k imagenet classes
 */
function imagenetClassesTopK(classProbabilities: any, k = 5) {
    console.log(classProbabilities);
    const probs =
      _.isTypedArray(classProbabilities) ? Array.prototype.slice.call(classProbabilities) : classProbabilities;

  const sorted = _.reverse(_.sortBy(probs.map((prob: any, index: number) => [prob, index]), (probIndex: Array<number> ) => probIndex[0]));

  const topK = _.take(sorted, k).map((probIndex: Array<number>) => {
    console.log(probIndex[0]);
    console.log(probIndex[1]);
    const iClass = imagesClasses[probIndex[1]];
    return {
      id: iClass[0],
      index: parseInt(probIndex[1].toString(), 10),
      name: iClass[1].replace(/_/g, ' '),
      probability: probIndex[0]
    };
  });
  return topK;
}

