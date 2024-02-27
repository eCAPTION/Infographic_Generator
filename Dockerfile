FROM python:3.8

RUN apt-get update && \
    apt-get install -y \
        git \
        python3-pip \
        python3-dev \
        libglib2.0-0

RUN sudo git clone https://github.com/zhuoyang125/const_layout.git
RUN cd const_layout

# install dependencies
# pytorch 1.8.1
RUN pip install torch==1.8.1+cpu torchvision==0.9.1+cpu torchaudio==0.8.1 -f https://download.pytorch.org/whl/torch_stable.html
# pytorch geometric 1.7.2
RUN pip install torch-geometric==1.7.2

RUN pip install -r requirements.txt

# download models
RUN ./download_model.sh
