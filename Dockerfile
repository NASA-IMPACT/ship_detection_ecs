FROM python:3.7
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends\
        build-essential \
        software-properties-common \
        libfreetype6-dev \
        libpng-dev \
        libzmq3-dev \
        libspatialindex-dev \
        gdal-bin \
        libgdal-dev \
        python3-gdal \
        libsm6 \
        vim \
        wget \
        zip \
        gcc \
        npm \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /ship_detection/
WORKDIR /ship_detection/
COPY . /ship_detection/
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG API_KEY

# install python package
RUN pip3 --no-cache-dir install setuptools && \
    pip3 --no-cache-dir install wheel && \
    pip3 install config && \
    pip3 install -r requirements.txt

RUN python3 code/message_consumer.py
