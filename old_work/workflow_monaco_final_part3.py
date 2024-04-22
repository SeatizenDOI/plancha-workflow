import os
import pandas as pd
from lib.lib_dcim import *
from lib.lib_tools import *
from datetime import datetime, timedelta, time
import numpy as np
from scipy.interpolate import interp1d
import math
import zipfile
import json
# open json file with config of the session
with open('../plancha_config/plancha_config.json') as json_file:
    cfg_prog = json.load(json_file)
cfg_prog['session_info']['session_name']
ORIGIN_ROOT = cfg_prog['session_info']['root']
SESSION_NAME = cfg_prog['session_info']['session_name']
NEW_DEST_ROOT = "/media/plancha/HDD_DATA/plancha_session/data_datapaper"
optional_place = cfg_prog['session_info']['optional_place']
session_name_device = cfg_prog['session_info']['device']
print("##############################################################################")
print("7 of 6 : WE ARE CHANGING THE TREE FOLDER OF : ", SESSION_NAME)
print("##############################################################################\n")
create_new_session_folder(ORIGIN_ROOT, NEW_DEST_ROOT, SESSION_NAME, optional_place, session_name_device, "REU")