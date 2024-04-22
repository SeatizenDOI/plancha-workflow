# -*- coding: utf-8 -*-
"""
PLANCHA UTILS:
    - Grab frames that are spatially close, inside a specified radius around reference corrdinates

@author: mjulien
"""

#%% IMPORT LIBRARIES 

import os
import pandas as pd
from datetime import datetime, timedelta, time
import numpy as np
import math
import shutil
import zipfile
import json
import sys
import time
from ExifData import *
import pyproj
import matplotlib.pyplot as plt

#%% Initialize

# source path
session_name = "20230506_MDG-IFATY_ASV-1_00"
root = "/media/bioeos/F/202305_plancha_session/"
frame_path = "/PROCESSED_DATA/FRAMES/"

# dest path
dest_root = "/media/bioeos/plancha_session_new_arbo/odm_reunion/"
# dest_path will be "FRAME_SUBSET_<location>_<radius>_<timestamp>/"

# Reference corrdinates and radius
# ex : Boucan canot : (-21.027347, 55.224767)
# ex : Aldabra passe-dubois : (-9.410898, 46.211001)
# ex : Aldabra arm06 : (-9.3734298, 46.2131298)
ref_lat = -23.14779873
ref_lon = 43.57333216
radius = 10 # in meter

#%% Read initial frame folder
files = os.listdir(root+session_name+frame_path)
files.sort()
print('Number of frames to analyze :', len(files))

#%% Read meta data and build datframe
data = []
names = []
print('Reading frames metadata')
for file in files:
    if file.endswith('.JPG') or file.endswith('.jpeg'):
            print('Reading image metadata - ' + file)
            file_path = root+session_name+frame_path+file
            # Extract metadata from a image
            focal_length, orientation, eo, maker = get_metadata(file_path)  # unit: m, _, ndarray
            # eo contains : longitude, latitude, altitude, roll, pitch, yaw
            eo = np.array(eo).astype(float) 
            data.append(eo)
            names.append(file)
cols = ['longitude', 'latitude', 'altitude', 'roll', 'pitch', 'yaw']
dfmeta = pd.DataFrame(data,columns=cols)
dfmeta['frames'] = names
print('Done ...')
print(dfmeta.head())

#%% Building projection from WGS84 to utm 40
wgs2utm = pyproj.Proj(proj='utm', zone='40', ellps='WGS84', south=True)
x_utm, y_utm = wgs2utm(np.array(dfmeta.longitude),np.array(dfmeta.latitude))
dfmeta['x_utm'] = x_utm
dfmeta['y_utm'] = y_utm

ref_x_utm, ref_y_utm = wgs2utm(np.array(ref_lon),np.array(ref_lat))

ref_dist = []
pt1 = [ref_x_utm, ref_y_utm]
for ind, row in dfmeta.iterrows():
      pt2 = [row.x_utm,row.y_utm,]
      ref_dist.append(math.dist(pt1,pt2))
dfmeta['ref_dist'] = ref_dist

# Set radius and grab frames
dfsubset = dfmeta[np.abs(dfmeta.ref_dist) <= radius]

# reset index for clean post-process
dfmeta = dfmeta.reset_index(drop=True)
dfsubset = dfsubset.reset_index(drop=True)
print('Will copy',len(dfsubset),'frames')

# %% Create destination folder and copy selected frames

dest_path = "/FRAMES_SUBSET_"
dest_path = dest_path + str(np.round(ref_lat,4))+'_'+str(np.round(ref_lon,4))+'_rad_'+str(radius)
dest_path = dest_path + '_' + str(int(time.time())) + 's/'

if os.path.exists(dest_root+session_name) ==  False:
    os.mkdir(dest_root+session_name)
if os.path.exists(dest_root+session_name+dest_path) == False:
    os.mkdir(dest_root+session_name+dest_path)

print('Destination path created at:',dest_root+session_name+dest_path)

print('Starting frames copy to destination folder')

for i in range(len(dfsubset)):
    src_path = root+session_name+frame_path
    dst_path = dest_root+session_name+dest_path
    frame = dfsubset.frames.iloc[i]
    print('copying',frame)
    shutil.copy(src_path+frame,dst_path+frame)
    print('done ...')

