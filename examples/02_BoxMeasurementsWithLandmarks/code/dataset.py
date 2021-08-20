# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import torch
import glob
import numpy as np
import cv2
import torchvision.transforms.functional as F
import random
import os
import math
from PIL import Image
from torchvision import transforms, models

class AugmentedObjectsDataset(torch.utils.data.Dataset):
    def __init__(self, dataset_path, samples=1000, img_side=416):
        self.samples = samples
        self.img_side = img_side
        file_list = glob.glob(os.path.join(dataset_path, "*.jpg"))
        self.data = []
        for filename in file_list:
            img = Image.open(filename).convert('RGB')
            # pad the image (make it square) if necessary
            w,h = img.size
            if w!=h:
                img_max_side=max(w,h)
                img_pad = Image.new('RGB', (img_max_side, img_max_side), (0,0,0))
                img_pad.paste(img, img.getbbox())  # Not centered, top-left corner
                img = img_pad
            label_filename = filename.replace('jpg', 'csv')            
            landmarks = np.fromfile(label_filename, dtype=np.int32, sep=',').reshape((8,2))            
            self.data.append((img, landmarks))
        if len(self.data) == 0: raise Exception(f'No images found at: {dataset_path}')
    
    def __rotate_around_point_lowperf__(self, point, radians, origin=(0, 0)):
        """Rotate a point around a given point.

        I call this the "low performance" version since it's recalculating
        the same values more than once [cos(radians), sin(radians), x-ox, y-oy).
        It's more readable than the next function, though.
        """
        x, y = point
        ox, oy = origin

        qx = ox + math.cos(radians) * (x - ox) + math.sin(radians) * (y - oy)
        qy = oy + -math.sin(radians) * (x - ox) + math.cos(radians) * (y - oy)

        return qx, qy
    
    def __preprocess__(self, img, landmarks):
        landmarks = np.array(landmarks)
        shape=(self.img_side, self.img_side)        
        w,h = img.size
        side = max(h,w)
        if random.random() < 0.3:
            # just resize
            img = F.resize(img, shape)
            for i,l in enumerate(landmarks):
                landmarks[i] = ( (l/(side,side)) * shape).astype(np.int32)
            w,h=(shape)
            
        else:
            # random crop
            top, left, h, w = transforms.RandomCrop.get_params(img, shape)
            img = F.crop(img, top, left, h, w)    
            for i,l in enumerate(landmarks):
                candidate = l - (left, top)
                if (candidate < 0).any():
                    landmarks[i] = (-1,-1)
                elif (candidate > (w,h)).any():
                    landmarks[i] = (-1,-1)
                else:
                    landmarks[i] = candidate
        
        # random flip
        if random.random() > .5:
            img = F.hflip(img)
            for l in landmarks: l[0] = w-l[0]
            for i in [(0,3),(1,2),(4,5),(6,7)]:
                landmarks[i[0]],landmarks[i[1]]=np.array(landmarks[i[1]]),np.array(landmarks[i[0]])
        
        # random rotate
        if random.random() > .5:
            angle = transforms.RandomRotation.get_params(degrees=(0,10))
            theta = np.radians(angle)
            img = F.rotate(img, angle)

            for i,l in enumerate(landmarks):
                landmarks[i] = self.__rotate_around_point_lowperf__(l, theta, (208,208))
        
        # random change pixel attributes
        if random.random() > 0.6:
            bri,con,sat,hue=random.random(),random.random(),random.random(),random.random()/2.0
            img = transforms.ColorJitter(brightness=bri, contrast=con, saturation=sat, hue=hue)(img)
            
        # random blur
        if random.random() > 0.6:
            img = transforms.GaussianBlur(kernel_size=(5, 9), sigma=(0.1, 5))(img)
                
        # normalize landmarks
        norm_landmarks = (landmarks / (w,h)).astype(np.float32)
        norm_landmarks = norm_landmarks.flatten()

        # normalize image (ImageNet normalization params)
        img = (np.array(img) / 255.0).astype(np.float32)
        img -= [0.406, 0.456, 0.485] # RGB
        img /= [0.225, 0.224, 0.229] # RGB
        
        return F.to_tensor(img), torch.from_numpy(norm_landmarks)
    
    def __len__(self):
        return self.samples
    
    def __getitem__(self, idx):
        img, landmarks = self.data[np.random.randint(0, len(self.data))]
        return self.__preprocess__(img, landmarks)
