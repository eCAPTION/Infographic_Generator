# Use the official Ubuntu 18.04 image as base
FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.8 python3-pip
# Update symlink to point to latest
RUN rm /usr/bin/python3 && ln -s /usr/bin/python3.8 /usr/bin/python3
RUN python3 --version
RUN pip3 --version

# install git
RUN apt-get install -y git

RUN git clone https://github.com/zhuoyang125/const_layout.git
RUN cd const_layout

# install dependencies
# pytorch 1.8.1
RUN python3 -m pip install torch==1.8.1+cpu -f https://download.pytorch.org/whl/torch_stable.html
# pytorch geometric 1.7.2
RUN python3 -m pip install torch-geometric==1.7.2

RUN python3 -m pip install -r requirements.txt

# download models
RUN ./download_model.sh
