ARG UBUNTU_VERSION=16.04

FROM nvidia/cuda:9.0-base-ubuntu${UBUNTU_VERSION} as base

# For CUDA profiling, TensorFlow requires CUPTI.
ENV LD_LIBRARY_PATH /usr/local/cuda/extras/CUPTI/lib64:$LD_LIBRARY_PATH

ARG PYTHON=python3

ENV TF_NEED_CUDA 1
ENV TF_NEED_TENSORRT 1
ENV TF_CUDA_COMPUTE_CAPABILITIES=3.5,5.2,6.0,6.1,7.0
ENV TF_CUDA_VERSION=9.0
ENV TF_CUDNN_VERSION=7

# NCCL 2.x
ENV TF_NCCL_VERSION=2

# See http://bugs.python.org/issue19846
ENV LANG C.UTF-8

COPY bashrc /etc/bash.bashrc

# install dependencies
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends\
        build-essential \
        cuda-command-line-tools-9-0 \
        cuda-cublas-9-0 \
        cuda-cufft-9-0 \
        cuda-curand-9-0 \
        cuda-cusolver-9-0 \
        cuda-cusparse-9-0 \
        gcc \
        gdal-bin \
        libcudnn7=7.2.1.38-1+cuda9.0 \
        libfreetype6-dev \
        libfreetype6-dev \
        libgdal-dev \
        libhdf5-serial-dev \
        libnccl2=2.2.13-1+cuda9.0 \
        libpng-dev \
        libpng12-dev \
        libsm6 \
        libspatialindex-dev \
        libzmq3-dev \
        libzmq3-dev \
        pkg-config \
        python3-dev \
        python3-gdal \
        python3-pip \
        python3.7 \
        software-properties-common \
        vim \
        && \
        && apt-get update \
        && apt-get install nvinfer-runtime-trt-repo-ubuntu1604-4.0.1-ga-cuda9.0 \
        && apt-get update \
        && apt-get install libnvinfer4=4.1.2-1+cuda9.0 \
        && apt-get update && apt-get install -y \
            ${PYTHON} \
            ${PYTHON}-pip \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* \
        && ln -s $(which ${PYTHON}) /usr/local/bin/python \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* # Copyright 2018 The TensorFlow Authors. All Rights Reserved.

RUN mkdir /ship_detection/
WORKDIR /ship_detection/
COPY . /ship_detection/
ARG API_KEY
ENV API_KEY $API_KEY

# install python package
RUN pip3 --no-cache-dir install setuptools && \
    pip3 --no-cache-dir install wheel && \
    pip3 install config && \
    pip3 install -r requirements.txt

ENTRYPOINT python3 /ship_detection/code/infer_message_consumer.py
