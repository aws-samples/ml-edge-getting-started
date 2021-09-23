# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import time
import math
import random as rnd
import cv2
import numpy as np

class Processor():
    def __init__(self, class_names, input_shape=(640, 640), threshold=0.5, iou_threshold=0.6, keep_ratio=True):
        """Constructor
        
        Args:
            class_names (list(str)): class names of the model
            input_shape (int,int): model's input shape (actual input is of shape [1, 3, input_shape[0], input_shape[1]])
            threshold (float): detections with scores lower than this will not be considered, lower value may produce more results
            iou_threshold (float): used for box IOU filtering, higher value may increase post-processing time
            keep_ratio (bool): if True then non-square input images will be made square prior to being resized to input size
        """
        self.input_shape = np.array(input_shape)
        self.class_names = class_names
        self.class_count = len(class_names)
        self.feature_count = self.class_count + 5 # outputs per anchor (bbox, confidence and class probabilities)
        self.threshold = threshold
        self.iou_threshold = iou_threshold
        self.keep_ratio = keep_ratio        
        self.strides = np.array([8., 16., 32.])
        self.grids = [self.__make_grid__(int(self.input_shape[0]/x), int(self.input_shape[1]/x)) for x in self.strides]
        anchors = np.array([
            [[10, 13], [16, 30], [33, 23]],
            [[30, 61], [62, 45], [59, 119]],
            [[116, 90], [156, 198], [373, 326]],
        ])
        self.nl = len(anchors)        
        a = anchors.copy().astype(np.float32)
        a = a.reshape(self.nl, -1, 2)
        self.anchors = a.copy()
        self.anchor_grid = a.copy().reshape(self.nl, 1, -1, 1, 1, 2)
        self.colors = [[rnd.randint(0, 255) for _ in range(3)] for _ in range(self.class_count)]
    
    def __make_grid__(self, nx, ny):
        yv, xv = np.meshgrid(np.arange(ny), np.arange(nx), indexing='ij')
        return np.stack((xv, yv), 2).reshape((1, 1, ny, nx, 2)).astype(np.float32)
    
    def post_process(self, preds, source_image_shape, image=None):
        z = []        
        for i,tensor in enumerate(preds):            
            tensor = 1/(1 + np.exp(-tensor)) # sigmoid
            tensor[..., 0:2] = (tensor[..., 0:2] * 2. - 0.5 + self.grids[i]) * self.strides[i]  # xy
            tensor[..., 2:4] = (tensor[..., 2:4] * 2) ** 2 * self.anchor_grid[i]  # wh
            z.append(tensor.reshape(tensor.shape[0], -1, self.feature_count))
        predictions = np.concatenate(z, axis=1)
        xc = predictions[..., 4] > self.threshold
        predictions = predictions[xc]
        bboxes, scores, cids = self.get_detections(predictions)
        
        # Normalise box coordinates to be in the range (0, 1]
        h, w = source_image_shape[:2]
        h1, w1 = h, w
        if self.keep_ratio and h != w:
            # Padding was used during pre-process to make the source image square
            h1 = w1 = max(h, w)
            
        y_scale,x_scale = (h1,w1) / self.input_shape.astype(np.float32) / (h,w)
        bboxes[:, (0, 2)] *= x_scale
        bboxes[:, (1, 3)] *= y_scale
        bboxes = np.clip(bboxes, 0, 1)
        
        if image is not None:
            self.draw_cv2(image, bboxes, scores, cids)

        return (bboxes, scores, cids), image

    def pre_process(self, image):
        pad_y, pad_x = 0, 0
        if self.keep_ratio:
            # Make the image square if needed by adding extra pads to
            # preserve the original height to width ratio after resize
            h, w = image.shape[:2]  
            if h != w:
                max_size = max(h, w)
                pad_y, pad_x = max_size - h, max_size - w
                img = np.zeros((max_size, max_size, 3), dtype="float32")
                img[0:max_size-pad_y, 0:max_size-pad_x] = image[:]
                image = img
        
        img = cv2.resize(image, (self.input_shape[0], self.input_shape[1]))
        img = img.astype(np.float32) / 255.
        
        # Convert to an expected shape
        img = img.transpose(2, 0, 1)  # to CHW
        img = np.expand_dims(img, axis=0).copy()  # Must use a copy here, otherwise it may not work as expected on Panorama
 
        return img 
    
    def non_max_suppression(self, bboxes, scores, cids):
        x1 = bboxes[:, 0]
        y1 = bboxes[:, 1]
        x2 = bboxes[:, 2]
        y2 = bboxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1) 
        order = scores.flatten().argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(iou <= self.iou_threshold)[0]
            order = order[inds + 1]
        bboxes = bboxes[keep]
        scores = scores[keep]
        cids = cids[keep]
        return bboxes, scores, cids

    def get_detections(self, predictions):
        bboxes = self.xywh2xyxy(predictions[..., 0:4])
        scores = np.amax(predictions[:, 5:], 1, keepdims=False)  # only highest score
        cids = np.argmax(predictions[:, 5:], axis=-1)
        return self.non_max_suppression(bboxes, scores, cids)

    def xywh2xyxy(self, x):
        """Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where x1y1=top-left, x2y2=bottom-right"""
        
        y = np.zeros_like(x)
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # x1
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # y1
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # x2
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # y2
        return y

    def draw_cv2(self, image, bboxes, scores, cids):
        """Draw the detection boxes on the given image"""
        
        # Box coordinates are normalised, convert to absolute and clip to image boundaries
        h, w = image.shape[:2]
        bboxes[:, (0, 2)] *= w
        bboxes[:, (1, 3)] *= h
        bboxes[:, (0, 2)] = np.clip(bboxes[:, (0, 2)], 0, w-1)
        bboxes[:, (1, 3)] = np.clip(bboxes[:, (1, 3)], 0, h-1)
        
        for bbox, score, cid in zip(bboxes.astype(int), scores, cids.astype(int)):
            label = f'{self.class_names[cid]} {score:.2f}'
            self.draw_box(image, bbox, label=label, color=self.colors[cid])

    def draw_box(self, image, bbox, label, color=None):
        if color is None:
            color = [rnd.randint(0, 255) for _ in range(3)]
        x1, y1, x2, y2 = bbox
        cv2.rectangle(image, (x1, y1), (x2, y2), color=color, thickness=5)

        # Assure label is visible
        h, w = image.shape[:2]
        thickness = 2 if w < 1000 else 3 if w < 2000 else 6
        font_scale = 0.8 if w < 1000 else 2 if w < 2000 else 3
        lbl_h = 20 if h < 1000 else 70 if h < 2000 else 150
        lbl_y1 = y1 - lbl_h
        lbl_y2 = y1
        if lbl_y1 < 0:
            lbl_y1, lbl_y2 = y2, y2 + lbl_h
        elif lbl_y2 > h:
            lbl_y1, lbl_y2 = y2 - lbl_h, y2
        cv2.rectangle(image, (x1, lbl_y1), (x2, lbl_y2), color=color, thickness=cv2.FILLED)
        cv2.putText(image, label, (x1 + 5, lbl_y2 - 2), cv2.FONT_HERSHEY_SIMPLEX, fontScale=font_scale,
                    color=(255, 255, 255), thickness=thickness, lineType=1)