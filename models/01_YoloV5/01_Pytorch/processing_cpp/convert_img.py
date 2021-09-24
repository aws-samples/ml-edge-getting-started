# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import cv2
import sys
import os
import numpy as np

# Sample image: https://i2.wp.com/petcaramelo.com/wp-content/uploads/2020/05/doberman-cores.jpg

## Use this script to prepare an image as an input tensor for the test
## It depends on OpenCV. This script decodes your image and saves a binary file with
## a squared/resized/squashed(between 0,1) version of the image in the format NHWC-RGB

if __name__=='__main__':
    if len(sys.argv) != 4:
        print("Invalid arguments")
        print("Usage:")
        print(f"$ python3 {sys.argv[0]} <IMAGE_PATH> <OUTPUT_FILE_PATH> <IMG_SIZE>")
        quit(1)
    if not os.path.exists(sys.argv[1]):
        print(f"Image file not found: {sys.argv[1]}")
        quit(1)
    if os.path.exists(sys.argv[2]):
        print(f"Output file already exists: {sys.argv[2]}")
        quit(1)
    img_size = int(sys.argv[3])
    img = cv2.imread(sys.argv[1])
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h,w,c = img.shape
    print(f"Original shape: {h}x{w}x{c} HWC BGR")
    if h!=w: # make it square
        max_size=max(h,w)
        new_img = np.zeros((max_size,max_size,c), dtype=np.uint8)
        new_img[:h, :w] = img
        img = new_img
    img = cv2.resize(img, (img_size,img_size))
    img = img.astype(np.float32) / 255.0
    img = img.transpose(2,0,1)
    img = img[np.newaxis, ...]
    print(f"Final shape: {img.shape} NHWC RGB")
    with open(sys.argv[2], 'wb') as f:
        f.write(img.flatten().tobytes())
