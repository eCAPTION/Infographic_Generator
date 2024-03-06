# Use the official Ubuntu 18.04 image as base
FROM python:3.8.10


# install git
RUN apt-get -qq -y update && \
    apt-get -qq -y upgrade && \
    apt-get install -y git wget

RUN git clone https://github.com/zhuoyang125/const_layout.git 
WORKDIR ./const_layout/

# install dependencies
RUN python3 -m pip install torch==1.8.1+cpu torchvision==0.9.1+cpu torchaudio==0.8.1 -f https://download.pytorch.org/whl/torch_stable.html
RUN python3 -m pip install torch-scatter==2.0.7 -f https://data.pyg.org/whl/torch-1.8.1+cpu.html
RUN python3 -m pip install torch-sparse==0.6.10 -f https://data.pyg.org/whl/torch-1.8.1+cpu.html
# pytorch geometric 1.7.2
RUN python3 -m pip install torch-geometric==1.7.2

# copy data files (requirement, model, dataset)

RUN python3 -m pip install -r requirements.txt

# download models
RUN chmod +x download_model.sh
RUN ./download_model.sh

# run the app
RUN chmod +x start.sh
EXPOSE 80
CMD ["./start.sh"]
