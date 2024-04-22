# -*- coding: utf-8 -*-

##############################################################################
###################### IMPORT LIBRARIES ######################################
##############################################################################

import os
import pandas as pd
from lib.lib_dcim import *
from lib.lib_bathy import *
from datetime import datetime, timedelta, time
import numpy as np
from scipy.interpolate import interp1d
import math
import zipfile
import json

##############################################################################
###################### PARAMETER DEFINITION ##################################
##############################################################################

# open json file with config of the session
with open('../plancha_config/plancha_config.json') as json_file:
    cfg_prog = json.load(json_file)
cfg_prog['session_info']['session_name']
ROOT = cfg_prog['session_info']['root']
SESSION_NAME = cfg_prog['session_info']['session_name']
PPK_CONFIG_PATH = cfg_prog['gps']['ppk_config_path']
# list of config files to run (files should have .conf ext)
ppk_cfgs = ["ppk_rtklib_20220310_v1"]  
# define frequence of frames
frames_per_second = cfg_prog['dcim']['frames_per_second']
exiftool_config_path = cfg_prog['dcim']['exiftool_config_path']
# for the leap second definition please refer to :
# https://fr.wikipedia.org/wiki/Synchronisation_GPS
leap_sec = int(cfg_prog['dcim']['leap_sec'])
# La Reunion only
rgp_station = cfg_prog['gps']['rgp_station']
# flag for filter on rtkfix data
flag_rtkfix =  cfg_prog['gps']['filt_rtkfix']
gpsbaseposition_mean_on_llh = cfg_prog['gps']['gpsbaseposition_mean_on_llh']
# derived paths and parameters
SESSION_PATH = ROOT + SESSION_NAME
VIDEOS_PATH = SESSION_PATH + "/DCIM/videos"
IMAGES_PATH = SESSION_PATH + "/DCIM/images"
FRAMES_PATH = VIDEOS_PATH + "/frames"
GPS_PATH = SESSION_PATH + "/GPS"
GPS_BASE_PATH = GPS_PATH + "/BASE"
GPS_DEVICE_PATH = GPS_PATH + "/DEVICE"
BATHY_PATH = SESSION_PATH + "/BATHY"
METADATA_PATH = SESSION_PATH + "/METADATA"
SENSORS_PATH = SESSION_PATH + "/SENSORS"
SESSION_INFO_PATH = METADATA_PATH +"/session_info.csv"
CSV_EXIFTOOL_FRAMES = METADATA_PATH + "/metadata.csv"
CSV_EXIFTOOL_VIDEO =  METADATA_PATH + "/csv_exiftool_video.csv"
delta_time = str(1/float(frames_per_second))
# N.B. insert the date and time following the format "YYYY:MM:DD HH:MM:SS.000"
# N.B. insert the time in UTC+0 format
time_first_frame = str(cfg_prog['dcim']['time_first_frame_UTC'])
# correct time by adding leap seconds to match GPS time (in 2023 it is 18 s)
d_date = datetime.strptime(time_first_frame , '%Y:%m:%d %H:%M:%S.%f') + pd.Timedelta(seconds = leap_sec)
time_first_frame = d_date.strftime('%Y:%m:%d %H:%M:%S.%f')
### write metadata on session_info file
write_session_info(SESSION_NAME, SESSION_INFO_PATH, frames_per_second, time_first_frame, leap_sec)
### compute GPS file (either with ppk or not)
if os.path.isdir(GPS_DEVICE_PATH) :
    LLH_PATH, flag_gps = compute_gps(SESSION_INFO_PATH, GPS_DEVICE_PATH, GPS_BASE_PATH, SESSION_NAME, time_first_frame, FRAMES_PATH, rgp_station, delta_time, PPK_CONFIG_PATH, ppk_cfgs, flag_rtkfix, gpsbaseposition_mean_on_llh)
    ### plot GPS accuracy
    TXT_PATH = GPS_position_accuracy(SESSION_INFO_PATH, LLH_PATH, GPS_DEVICE_PATH, flag_rtkfix)
    ### run bathy analysis if possible
    #df_bathy = run_bathy_analysis(cfg_prog, BATHY_PATH, TXT_PATH, SENSORS_PATH)
    #run_bathy_postprocessing(df_bathy, cfg_prog, BATHY_PATH)
    ### compute and add metadata to frames
    time_calibration_and_geotag(time_first_frame, frames_per_second, flag_gps, exiftool_config_path, BATHY_PATH, METADATA_PATH, FRAMES_PATH, VIDEOS_PATH, SESSION_INFO_PATH, CSV_EXIFTOOL_FRAMES, TXT_PATH)



