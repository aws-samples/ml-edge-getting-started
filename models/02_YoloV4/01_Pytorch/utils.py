# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# 
# Parts of the code were replicated from:
# Copyright Wong Kin Yiu: https://github.com/WongKinYiu/PyTorch_YOLOv4

import cv2
import numpy as np
import time

# Use the notebook from https://github.com/aws-samples/ml-edge-getting-started
# to compute the correct anchors and stride for the network you're using
# The following values are for yolov4-tiny
anchors = [[[81, 82], [135, 169], [344, 319]], [[23, 27], [37, 58], [81, 82]]]
stride = [32, 16, 8]

batch_size = 1
num_classes = 80

def preprocess_img(img, img_size=416):
    '''
    Preprocess an OpenCV raw image and prepare
    it for the format expected by the network
    '''
    # img is a raw BGR cv2 image
    h,w,c = img.shape
    if h!=w: # make a square to keep the aspect ratio
        cur_img_size = max(w,h)
        img_ = np.zeros((cur_img_size,cur_img_size,c), dtype=np.uint8)
        img_[0:h, 0:w] = img
        img = img_
    img = cv2.resize(img, (img_size, img_size))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.transpose(2,0,1).astype(np.float32) / 255.0
    return img

def nms(bboxes, scores, iou_threshold):
    '''
    Non Maximum Suppresion 
    '''
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
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    bboxes = bboxes[keep]
    scores = scores[keep]
    return bboxes, scores

def xywh2xyxy(x):
    '''
     Transform box coordinates from [x, y, w, h] to [x1, y1, x2, y2] (where xy1=top-left, xy2=bottom-right)
    '''
    y = np.zeros_like(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
    y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
    y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
    y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
    return y

def non_max_suppression(prediction, conf_thres=0.1, iou_thres=0.6, merge=False, classes=None, agnostic=False):
    '''Performs Non-Maximum Suppression (NMS) on inference results
    Returns:
          detections with shape: nx6 (x1, y1, x2, y2, conf, cls)
    '''
    # expteced prediction shape --> (batch_size,2535,num_classes+5)
    nc = prediction[0].shape[1] - 5  # number of classes
    xc = prediction[..., 4] > conf_thres  # candidates
    # Settings
    min_wh, max_wh = 2, 4096  # (pixels) minimum and maximum box width and height
    max_det = 300  # maximum number of detections per image
    time_limit = 10.0  # seconds to quit after
    redundant = True  # require redundant detections
    multi_label = nc > 1  # multiple labels per box (adds 0.5ms/img)

    output = [None] * prediction.shape[0]
    for xi, x in enumerate(prediction):  # image index, image inference
        # Apply constraints
        x = x[xc[xi]]  # confidence

        # If none remain process next image
        if not x.shape[0]:
            continue

        # Compute conf
        x[:, 5:] *= x[:, 4:5]  # conf = obj_conf * cls_conf

        # Box (center x, center y, width, height) to (x1, y1, x2, y2)
        box = xywh2xyxy(x[:, :4])

        # Detections matrix nx6 (xyxy, conf, cls)
        if multi_label:
            i,j = np.array((x[:, 5:] > conf_thres).nonzero())
            x = np.concatenate((box[i], x[i, j + 5, None], j[:, None]), axis=1)
        else:  # best class only
            conf, j = x[:, 5:].max(1, keepdim=True)
            x = np.concatenate((box, conf, j), axis=1)[conf.view(-1) > conf_thres]

        # Filter by class
        if classes:
            x = x[(x[:, 5:6] == classes).any(1)]

        # If none remain process next image
        n = x.shape[0]  # number of boxes
        if not n:
            continue
        # Batched NMS
        c = x[:, 5:6] * (0 if agnostic else max_wh)  # classes
        boxes, scores = x[:, :4] + c, x[:, 4]  # boxes (offset by class), scores
        boxes,scores = nms(boxes, scores, iou_thres)
        i = np.array([a for a in range(len(boxes))])
        if i.shape[0] > max_det:  # limit detections
            i = i[:max_det]
        if merge and (1 < n < 3E3):  # Merge NMS (boxes merged using weighted mean)
            try:  # update boxes as boxes(i,4) = weights(i,n) * boxes(n,4)
                iou = box_iou(boxes[i], boxes) > iou_thres  # iou matrix
                weights = iou * scores[None]  # box weights
                x[i, :4] = np.matmul(weights, x[:, :4]) / weights.sum(1, keepdim=True)  # merged boxes
                if redundant:
                    i = i[iou.sum(1) > 1]  # require redundancy
            except:  # possible CUDA error https://github.com/ultralytics/yolov3/issues/1139
                #print(x, i, x.shape, i.shape)
                pass

        output[xi] = x[i]

    return output

def sigmoid(z):
    '''
    Sigmoid function
    '''
    return 1/(1 + np.exp(-z))

def create_grids(ng=(13, 13)):
    '''
    Create grids to support the anchors
    '''
    nx, ny = ng  # x and y grid size
    ng = (float(ng[0]),float(ng[1]))
    xv,yv = np.meshgrid(np.arange(ny), np.arange(nx))
    return np.stack((xv, yv), 2).reshape((1, 1, ny, nx, 2)).astype(np.float32)

def get_pred(io, stride, anchors):
    '''
    Convert the anchors+grids into
    '''
    anchor_wh = (np.array(anchors) / stride).reshape(1, len(anchors), 1, 1, 2)
    bs, _, ny, nx,no = io.shape
    grid = create_grids((nx,ny))
    io[..., :2] = (io[..., :2] * 2. - 0.5 + grid)
    io[..., 2:4] = (io[..., 2:4] * 2) ** 2 * anchor_wh
    io[..., :4] *= stride
    return io.reshape(batch_size, -1, no)

def detect(pred,conf_tresh=0.4, iou_tresh=0.5, merge=False):
    '''
    Get the two outputs of the network
    apply sigmoid, grids and concatenate
    exptected input shapes = [(batch_size,3,13,1,num_classes+5), (batch_size,3,26,26,num_classes+5)]
    '''
    pred = np.concatenate([get_pred(sigmoid(p), stride[i],anchors[i]) for i,p in enumerate(pred)], axis=1)
    preds = non_max_suppression(pred, conf_tresh, iou_tresh, merge)
    detections = []
    for det in preds:
        if det is None: continue
        for *xyxy, conf, cls in det:
            c1, c2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))
            detections.append([c1,c2,conf,cls])
    return detections
