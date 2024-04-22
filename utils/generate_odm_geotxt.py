# -*- coding: utf-8 -*-
"""
PLANCHA UTILS:
    - Generate ODM geo.txt file with corrdinates and attitude

@author: mjulien
"""

#%% IMPORT LIBRARIES ######################################
##############################################################################

import os
import pandas as pd
from datetime import datetime, timedelta, time
import numpy as np
import zipfile
import json
import sys
import time
from ExifData import *
import pyproj

#%% Initialize

# session_name = "20230906_REU-BOUCAN_ASV-1_01" # "20221023_SYC-DUBOIS_ASV-1_02"
session_name = "20221022_SYC-ALDARM06_ASV-1_01"
# session_name = "20221023_SYC-DUBOIS_ASV-1_02"
# root = "E:/test_plancha_postprocess/plancha_session/"
root = "E:/test_plancha_postprocess/odm_project/"
# frame_path = "/PROCESSED_DATA/FRAMES/"
# frame_path = "/FRAMES_MANUAL_SELECTED/frames_shortset_01/"
frame_path = "/FRAMES_SUBSET_-9.3734_46.2131_rad_30_1698667597s/"

#%% List files

files_list = os.listdir(root+session_name+frame_path)
files = files_list
files.sort()
print(files_list)

#%% Generate geo.txt for ODM

# Set projection 
epsg = 4326 # WGS 84

print('geotxt log')
with open(root+session_name+frame_path+'geo.txt', 'w') as geotxt:
    geotxt.write('EPSG:'+str(epsg)+'\n')
    for file in files:
        if file.endswith('.JPG') or file.endswith('.jpeg'):
                # print('Reading image metadata - ' + file)
                start_time = time.time()
                file_path = root+session_name+frame_path+file

                # Extract metadata from a image
                focal_length, orientation, eo, maker = get_metadata(file_path)  # unit: m, _, ndarray

                # eo contains : longitude, latitude, altitude, roll, pitch, yaw
                yaw = np.mod(eo[5]+180,360)-180
                pitch = np.mod(eo[4]+180,360)-180
                roll = np.mod(eo[3]+180,360)-180

                # data = np.array((eo[0],eo[1],eo[2],yaw,pitch,roll))
                data = np.array((eo[0],eo[1],eo[2],yaw,pitch,roll))
                linebuf = file + ' '
                for x in data:
                     linebuf = linebuf + str(x) +' '
                # print(linebuf)

                geotxt.write(linebuf+'\n')

#%% Generate flightlog.txt for reality cam

# Set projection
epsg = 32740 # Reunion, utm 40
wgs2utm = pyproj.Proj('EPSG:'+str(epsg))

print('flight log')
with open(root+session_name+frame_path+'flightlog.txt', 'w') as logtxt:
    logtxt.write(str(wgs2utm)+'\n')
    for file in files:
        if file.endswith('.JPG') or file.endswith('.jpeg'):
                # print('Reading image metadata - ' + file)
                start_time = time.time()
                file_path = root+session_name+frame_path+file

                # Extract metadata from a image
                focal_length, orientation, eo, maker = get_metadata(file_path)  # unit: m, _, ndarray

                #Building projection from WGS84 to utm 40
                x_utm, y_utm = wgs2utm(np.array(eo[0]),np.array(eo[1]))

                # eo contains : longitude, latitude, altitude, roll, pitch, yaw
                yaw = np.mod(eo[5]+180,360)-180
                pitch = np.mod(eo[4]+180,360)-180
                roll = np.mod(eo[3]+180,360)-180
                data = np.array((x_utm,y_utm,eo[2]))
                data = np.hstack((data,0.5,0.5,0.5))
                data = np.hstack((data,yaw,pitch,roll))
                linebuf = file + ' '
                for x in data:
                     linebuf = linebuf + str(x) +' '
                # print(linebuf)
                
                logtxt.write(linebuf+'\n')

