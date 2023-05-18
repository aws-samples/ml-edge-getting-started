// Original Copyright Microsoft Corporation. Licensed under the MIT License.
// Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import Jimp from 'jimp';
import {Tensor} from 'onnxruntime-web';

// 2022-08-19: Amazon modification.
export async function getImageTensorFromPath(imagePath: string, dims: number[] = [1, 3, 224, 224]): Promise<Tensor> {
    // 1. load the image
    var image = await loadImageFromPath(imagePath, dims[2], dims[3]);
    // 2. convert to tensor
    var imageTensor = imageDataToTensor(image, dims);
// End of Amazon modification.

    // 3. return the tensor
    return imageTensor;
}

export async function loadImageFromPathNoResize(path: string): Promise<Jimp> {
    // Use Jimp to load the image.
    var imageData = await Jimp.read(path);

    return imageData;
}

async function loadImageFromPath(path: string, width: number = 224, height: number = 224): Promise<Jimp> {
    // Use Jimp to load the image and resize it.
    var imageData = await Jimp.read(path).then((imageBuffer: Jimp) => {
        return imageBuffer.resize(width, height);
    });

    return imageData;
}

function imageDataToTensor(image: Jimp, dims: number[]): Tensor {
    // 1. Get buffer data from image and create R, G, and B arrays.
    var imageBufferData = image.bitmap.data;
    const [redArray, greenArray, blueArray] = new Array(new Array<number>(), new Array<number>(), new Array<number>());

    // 2. Loop through the image buffer and extract the R, G, and B channels
    for (let i = 0; i < imageBufferData.length; i += 4) {
        redArray.push(imageBufferData[i]);
        greenArray.push(imageBufferData[i + 1]);
        blueArray.push(imageBufferData[i + 2]);
        // skip data[i + 3] to filter out the alpha channel
    }

    // 3. Concatenate RGB to transpose [224, 224, 3] -> [3, 224, 224] to a number array
    const transposedData = redArray.concat(greenArray).concat(blueArray);

    // 4. convert to float32
    let i, l = transposedData.length; // length, we need this for the loop
    // create the Float32Array size 3 * 224 * 224 for these dimensions output
    const float32Data = new Float32Array(dims[1] * dims[2] * dims[3]);
    for (i = 0; i < l; i++) {
        float32Data[i] = transposedData[i] / 255.0; // convert to float
    }
    // 5. create the tensor object from onnxruntime-web.
    const inputTensor = new Tensor("float32", float32Data, dims);
    return inputTensor;
}


