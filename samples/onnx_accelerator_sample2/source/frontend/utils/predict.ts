// Original Copyright Microsoft Corporation. Licensed under the MIT License.
// Modifications Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

// Language: typescript
// Path: react-next\utils\predict.ts
import { getImageTensorFromPath } from './imageHelper';
import { runModelInference } from './modelHelper';

export async function analyzeImage(imagePath: string): Promise<any> {
  // 1. Convert image to tensor
  const imageTensor = await getImageTensorFromPath(imagePath, [1, 3, 224, 224]);
  // 2. Run model

  // 2022-08-19: Amazon addition.
  const response = await runModelInference(imageTensor);
  // 3. Return predictions and the amount of time it took to inference.
  return response;
  // End of Amazon addition.
}

