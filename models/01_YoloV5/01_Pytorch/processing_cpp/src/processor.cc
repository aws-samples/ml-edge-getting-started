// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

#include "processor.hpp"
#include "xtensor/xio.hpp"
#include "xtensor/xview.hpp"
#include "xtensor/xindex_view.hpp"
#include "xtensor/xbuilder.hpp"
#include "xtensor/xstrided_view.hpp"
#include "xtensor/xsort.hpp"
#include "xtensor/xmasked_view.hpp"
#include "xtensor/xadapt.hpp"
#include "xtensor/xnpy.hpp"
#include "xtensor/xmanipulation.hpp"

// just one instance per process
Processor Processor::singleton;

vecf Processor::prepareImage(const vecu& image, bool keepAspectRatio ) {
    // convert a raw RGB image to CHW. Make it square to keep aspect ration if required
    vecf img;
    if (keepAspectRatio) {
        auto shape = image.shape();
        unsigned long imgSize = shape[0];
        if (shape[0] != shape[1]) imgSize = std::max(shape[0], shape[1]);
        img = xt::zeros<float>({imgSize, imgSize, shape[2]});
        xt::view(img, xt::range(0, shape[0]), xt::range(0, shape[1]), xt::all()) = image;
    } else {
        img = image;
    } // else
    img /= 255;
    return xt::transpose(img, {2,0,1});
}

vecf Processor::makeGrid(long unsigned int nx, long unsigned int ny ) {
    auto mesh = xt::meshgrid(xt::arange<float>(ny), xt::arange<float>(nx));
    vecf grid = xt::stack(xt::xtuple(xt::get<1>(mesh), xt::get<0>(mesh)), 2);
    grid.reshape({1,1,ny,nx, 2});
    return grid;
}

void Processor::updateModelInput(unsigned int inputWidth, unsigned int inputHeight, unsigned int numberClasses) {
    this->numClasses = numberClasses;
    this->featureCount = this->numClasses + 5; /* num_classes + 5*/
    this->width = inputWidth;
    this->height = inputHeight;
    for (unsigned int i=0; i < 3; ++i ) {    
        this->grids[i] = makeGrid(inputWidth/strides[i], inputHeight/strides[i]);
    } // for
}

void Processor::nms(std::tuple<vecf,vecf,vecf>& detections, float iou_threshold) {
    vecf& bboxes = xt::get<0>(detections);
    vecf& scores = xt::get<1>(detections);
    vecf& cids = xt::get<2>(detections);
    // extract each axis of the bboxes
    vecf x1 = xt::view(bboxes, xt::all(), 0);
    vecf y1 = xt::view(bboxes, xt::all(), 1);
    vecf x2 = xt::view(bboxes, xt::all(), 2);
    vecf y2 = xt::view(bboxes, xt::all(), 3);
    // compute the areas of each bbox
    vecf areas = (x2 - x1 + 1) * (y2 - y1 + 1);
    // sort the scores - reverse order
    vecf ord = xt::argsort( xt::flatten(scores) );
    vecf order(ord.shape());
    std::copy(ord.crbegin(), ord.crend(), order.begin());

    // compute intersections
    std::vector<size_t> keep;
    while (order.size() > 0 ) {
        int i = order[0];
        keep.push_back(i);
        vecs rest = xt::view(order, xt::range(1, xt::placeholders::_));
        vecf xx1 = xt::maximum(x1[i], xt::view(x1, xt::keep(rest)));
        vecf yy1 = xt::maximum(y1[i], xt::view(y1, xt::keep(rest)));
        vecf xx2 = xt::minimum(x2[i], xt::view(x2, xt::keep(rest)));
        vecf yy2 = xt::minimum(y2[i], xt::view(y2, xt::keep(rest)));

        vecf w = xt::maximum(0.0, xx2 - xx1 + 1);
        vecf h = xt::maximum(0.0, yy2 - yy1 + 1);
        vecf inter = w * h;
        vecf iou = inter / (areas[i] + xt::view(areas, xt::keep(rest)) - inter);
        vecs inds = xt::ravel_indices(xt::argwhere(iou <= iou_threshold), iou.shape());
        inds += 1;
        order = xt::view(order, xt::keep(inds));
    } // while
    // keep only the bboxes selected by nms
    bboxes = xt::view(bboxes, xt::keep(keep));
    scores = xt::view(scores, xt::keep(keep));
    cids = xt::view(cids, xt::keep(keep));
}

std::tuple<vecf,vecf,vecf> Processor::getDetections(const vecf& predictions, float iou_threshold ) {
    // organize the outputs into bboxes, scores and class ids (cids)
    // the last dim has: 5 + 80
    // bboxes=0-3
    vecf bboxes = xywh2xyxy(xt::strided_view(predictions, {xt::ellipsis(), xt::range(0,4)}));    
    // view=5-
    auto view = xt::view(predictions, xt::all(), xt::range(5, xt::placeholders::_));
    vecf scores = xt::amax( view, {1} );
    vecf cids = xt::argmax( view, -1);    
    std::tuple<vecf,vecf,vecf> detections(bboxes, scores, cids);
    // invoke Non maximum suppression
    nms(detections, iou_threshold);
    vecf& selectedBboxes = xt::get<0>(detections);
    // normalize all bboxes
    xt::view(selectedBboxes, xt::all(), 0) /= width; // x1
    xt::view(selectedBboxes, xt::all(), 1) /= height; // y1
    xt::view(selectedBboxes, xt::all(), 2) /= width; // x2
    xt::view(selectedBboxes, xt::all(), 3) /= height; // y2
    selectedBboxes = xt::clip(selectedBboxes, 0.0, 1.0);
    return detections;
}

vecf Processor::xywh2xyxy(const vecf& x) {
    // Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where x1y1=top-left, x2y2=bottom-right
    vecf y = xt::zeros_like(x);
    xt::view(y, xt::all(), 0) = xt::view(x, xt::all(), 0) - xt::view(x, xt::all(), 2) / 2.0;
    xt::view(y, xt::all(), 1) = xt::view(x, xt::all(), 1) - xt::view(x, xt::all(), 3) / 2.0;
    xt::view(y, xt::all(), 2) = xt::view(x, xt::all(), 0) + xt::view(x, xt::all(), 2) / 2.0;
    xt::view(y, xt::all(), 3) = xt::view(x, xt::all(), 1) + xt::view(x, xt::all(), 3) / 2.0;
    return y;
}

std::tuple<vecf,vecf,vecf> Processor::detect(std::vector<vecf>& pred, float threshold, float iou_threshold ) { 
    for (size_t i=0; i < pred.size(); ++i ) {
        std::for_each(pred[i].begin(), pred[i].end(), sigmoid);
        auto sliceA = xt::strided_view(pred[i], {xt::ellipsis(), xt::range(0,2) });
        auto sliceB = xt::strided_view(pred[i], {xt::ellipsis(), xt::range(2,4) });
        sliceA = (sliceA * 2.0 - 0.5 + grids[i]) * strides[i];
        sliceB = xt::pow(sliceB * 2.0, 2) * xt::strided_view(anchorGrid, {i, xt::ellipsis()});
        pred[i].reshape({1, -1, featureCount});
    } // for
    // Workaround to avoid concatenate and improve performance
    vecf predictions = xt::zeros<float>({pred[0].size() + pred[1].size() + pred[2].size()});
    std::copy(pred[0].begin(), pred[0].end(), predictions.begin());
    std::copy(pred[1].begin(), pred[1].end(), predictions.begin()+pred[0].size());
    std::copy(pred[2].begin(), pred[2].end(), predictions.begin()+pred[0].size()+pred[1].size());
    predictions.reshape({1,-1,numClasses + 5});

    auto sliceC = xt::strided_view(predictions, {xt::ellipsis(), 4});
    vecs idx = xt::ravel_indices(xt::argwhere(sliceC > threshold), predictions.shape());
    vecf resp = xt::view(predictions, xt::all(), xt::keep(idx), xt::all());

    if (resp.size() > 0) {
        return getDetections(xt::squeeze(resp), iou_threshold);
    } else {
        throw std::invalid_argument("No object found!");
    } // else
}
