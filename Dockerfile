# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Install lib, create user.
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ffmpeg libimage-exiftool-perl rtklib gdal-bin && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir \
    numpy==2.2.4 \
    ffmpeg-python==0.2.0 \
    folium==0.19.5 \
    geocube==0.7.1 \
    hatanaka==2.8.1 \
    open3d==0.19.0 \
    pycountry==24.6.1 \
    PyExifTool==0.5.6 \
    pymavlink==2.4.43 \
    pytz==2025.2 \
    transforms3d==0.4.2 \
    wget==3.2 \
    natsort==8.4.0 \
    pandas==2.2.3 \
    useradd -ms /bin/bash seatizen

# Add local directory and change permission.
ADD --chown=seatizen ../. /home/seatizen/app/

# Setup workdir in directory.
WORKDIR /home/seatizen/app

# Change with our user.
USER seatizen

# Define the entrypoint script to be executed.
ENTRYPOINT ["python", "workflow.py"]