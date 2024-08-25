# Use an official Python runtime as a parent image
FROM python:3.9-slim-bullseye

# Install lib, create user.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ffmpeg libimage-exiftool-perl rtklib gdal-bin && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir \
    numpy==1.26.4 \
    ffmpeg-python==0.2.0 \
    folium==0.16.0 \
    geocube==0.4.2 \
    hatanaka==2.8.1 \
    open3d==0.18.0 \
    pycountry==23.12.11 \
    PyExifTool==0.5.6 \
    pymavlink==2.4.41 \
    pytz==2024.1 \
    transforms3d==0.4.1 \
    wget==3.2  \
    natsort==8.4.0 && \
    useradd -ms /bin/bash seatizen

# Add local directory and change permission.
ADD --chown=seatizen ../. /home/seatizen/app/

# Setup workdir in directory.
WORKDIR /home/seatizen/app

# Change with our user.
USER seatizen

# Define the entrypoint script to be executed.
ENTRYPOINT ["python", "/home/seatizen/app/workflow.py"]