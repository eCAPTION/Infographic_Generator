FROM pytorch/pytorch:1.8.1-cuda11.1-cudnn8-runtime

RUN apt-get update && \
    apt-get install -y \
        git \
        python3-pip \
        python3-dev \
        libglib2.0-0
RUN git clone https://github.com/zhuoyang125/const_layout.git

