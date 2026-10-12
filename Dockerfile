# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Bullseye is past regular/LTS mirror life: live deb.debian.org security
# indexes still list packages whose .debs 404. Point apt at archive.debian.org
# so the existing package set keeps installing. Check-Valid-Until is off because
# archived Release files are expired by design.
RUN sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g' /etc/apt/sources.list \
 && sed -i 's|http://deb.debian.org/debian-security|http://archive.debian.org/debian-security|g' /etc/apt/sources.list \
 && printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid \
 && apt-get update && apt-get install -y --no-install-recommends \
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
    pandas==2.2.3 && \
    useradd -ms /bin/bash seatizen

# Add local directory and change permission.
ADD --chown=seatizen ../. /home/seatizen/app/

# Setup workdir in directory.
WORKDIR /home/seatizen/app

# Change with our user.
USER seatizen

# Define the entrypoint script to be executed.
ENTRYPOINT ["python", "workflow.py"]
