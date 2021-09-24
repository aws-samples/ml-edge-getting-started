// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

#ifndef PROCESSOR_H
#define PROCESSOR_H

#include <iostream>
#include <cmath>
#include <vector>
#include "xtensor/xarray.hpp"

typedef xt::xarray<float> vecf;
typedef xt::xarray<size_t> vecs;
typedef xt::xarray<unsigned char> vecu;

/*
 * Pre and post processing functions for Yolov5
 */
class Processor {
    public:
        
        virtual ~Processor() {};
        
        static Processor& get() { return singleton; }

        vecf prepareImage(const vecu& image, bool keepAspectRatio=false);

        void updateModelInput(unsigned int inputWidth=640, unsigned int inputHeight=640, unsigned int numberClasses=80);

        // get the raw output from Yolo and compute bboxes, scores and class ids
        std::tuple<vecf,vecf,vecf> detect(std::vector<vecf>& pred, float threshold=0.25, float iou_threshold=0.45 );

    private:
        Processor() :
            strides{8.0, 16.0, 32.0},
            anchors{{{10,13},  {16,30}, {33,23}},
                    {{30,61}, {62,45}, {59,119}},
                    {{116,90}, {156,198}, {373,326}}} {
                int nl = anchors.dimension();
                anchorGrid = anchors;
                anchorGrid.reshape({nl, 1, -1,1,1,2});
                updateModelInput();
        }

        static Processor singleton;

        static constexpr auto sigmoid = [](float& x) { x = 1.0/ (1.0 + std::exp(-x)); };

        // helper functions
        vecf makeGrid(long unsigned int nx, long unsigned int ny );
        vecf xywh2xyxy(const vecf& x);

        std::tuple<vecf,vecf,vecf> getDetections(const vecf& predictions, float iou_threshold );
        // non maximum suppression
        void nms(std::tuple<vecf,vecf,vecf>& detections, float iou_threshold);

        int width;
        int height;
        int numClasses;
        vecf strides;
        vecf grids[3];
        vecf anchors;

        vecf anchorGrid;
        int featureCount;
};
#endif // PROCESSOR_H
