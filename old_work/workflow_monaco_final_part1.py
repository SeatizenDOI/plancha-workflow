import os
import pandas as pd
from lib.lib_dcim import *
from lib.lib_tools import print_plancha_header, clear_processed_session
from datetime import datetime, timedelta, time
import numpy as np
from scipy.interpolate import interp1d
import math
import zipfile
import json
print_plancha_header()
# open json file with config of the session
with open('../plancha_config/plancha_config.json') as json_file:
    cfg_prog = json.load(json_file)
cfg_prog['session_info']['session_name']
ROOT = cfg_prog['session_info']['root']
SESSION_NAME = cfg_prog['session_info']['session_name']
# define frequence of frames
frames_per_second = cfg_prog['dcim']['frames_per_second']
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
# clear session if already exist
if cfg_prog['session_info']['delete_processed_session'] :
    clear_processed_session(FRAMES_PATH, BATHY_PATH, METADATA_PATH, GPS_BASE_PATH, GPS_DEVICE_PATH)
print("##############################################################################")
print("0 of 6 : WE ARE PROCESSING THE FOLLOWING SESSION : ", SESSION_NAME)
print("##############################################################################\n")
split_videos(VIDEOS_PATH, FRAMES_PATH, frames_per_second, SESSION_NAME, METADATA_PATH)
