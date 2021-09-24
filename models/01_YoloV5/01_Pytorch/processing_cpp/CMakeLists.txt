#
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#

cmake_minimum_required(VERSION 3.5.1)

set(CMAKE_CXX_STANDARD 17)

project(processor C CXX)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libstdc++")
set(XTENSOR_USE_XSIMD 1)

set(MODEL_PATH "")
if (NOT IS_ABSOLUTE ${MODEL_PATH})
    message(FATAL_ERROR "You need to point MODEL_PATH to the Absolute path of the model's dir")
    return(1)
endif()

include(FetchContent)

FetchContent_Declare(
  xtl
  GIT_REPOSITORY https://github.com/xtensor-stack/xtl.git
  GIT_TAG "0.7.2"
)

FetchContent_Declare(
  xtensor
  GIT_REPOSITORY https://github.com/xtensor-stack/xtensor.git
  GIT_TAG "0.21.10"
)

FetchContent_Declare(
  xsimd
  GIT_REPOSITORY https://github.com/xtensor-stack/xsimd.git
  GIT_TAG "7.4.8"
)


FetchContent_MakeAvailable(xtl xsimd xtensor)
find_package(xtl REQUIRED PATHS "${xtl_BINARY_DIR}")
find_package(xsimd REQUIRED PATHS "${xsimd_BINARY_DIR}")
find_package(xtensor REQUIRED PATHS "${xtensor_BINARY_DIR}")

include_directories(
    "${CMAKE_CURRENT_BINARY_DIR}"
    "include"
    "${xtensor_SOURCE_DIR}/include"
    "${xtl_SOURCE_DIR}/include"
    "${xsimd_SOURCE_DIR}/include"
    "${MODEL_PATH}"
)
link_directories("${MODEL_PATH}")

add_library(processor SHARED src/processor.cc)
target_link_libraries(processor xtensor::optimize)
target_compile_options(processor PRIVATE -march=native -ffast-math)

add_executable(test src/test.cc)
target_link_libraries(test processor xtensor::optimize dlr)
target_compile_options(test PRIVATE -march=native -ffast-math)
