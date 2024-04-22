# -*- coding: utf-8 -*-

import json
from lib.lib_dcim import *
from lib.lib_tools import *
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
VIDEOS_PATH = SESSION_PATH + "/DCIM"
METADATA_PATH = SESSION_PATH + "/METADATA"
SENSORS_PATH = SESSION_PATH + "/SENSORS"
GPS_PATH = SESSION_PATH + "/GPS"
GPS_BASE_PATH = GPS_PATH + "/BASE"
GPS_DEVICE_PATH = GPS_PATH + "/DEVICE"
PROCESSED_PATH = SESSION_PATH + "/PROCESSED_DATA"
FRAMES_PATH = PROCESSED_PATH + "/FRAMES"
BATHY_PATH = PROCESSED_PATH + "/BATHY"

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
