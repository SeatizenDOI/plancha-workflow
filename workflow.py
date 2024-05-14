# -*- coding: utf-8 -*-

import os
import csv
import json
import argparse
import traceback
import pandas as pd
from pathlib import Path
from datetime import datetime

from lib.lib_dcim import *
from lib.lib_bathy import *
from lib.lib_gps import compute_gps, GPS_position_accuracy, compute_gps_for_only_device
from lib.lib_tools import *

def parse_option():
    parser = argparse.ArgumentParser(prog="plancha-workflow", description="Workflow between raw data and Seatizen data")

    parser.add_argument("-csv", default=None, help="Path to csv file for session_name")
    parser.add_argument("-os", "--only-split", action="store_true", help="Only split images from videos")
    parser.add_argument("-ns", "--no-split", action="store_true", help="Don't split images from videos")
    parser.add_argument("-na", "--no_annotate", action="store_true", help="Don't annotate images")
    parser.add_argument("-nb", "--no_bathy", action="store_true", help="Don't process bathy")
    parser.add_argument("-nc", "--no_clean", default="", help="Specify folder to clean f: FRAMES, m: METADATA, b: BATHY, g: GPS, Ex: -no_clean fm")
    parser.add_argument("-frgp", "--force_use_rgp", action="store_true", help="Force to use RGP station to compute base gps")
    parser.add_argument("-rp", "--root_path", default=None, help="Root path for the session")
    parser.add_argument("-rf", "--remove_frames", default=None, help="Remove frames until meet the number")
    parser.add_argument("-pcn", "--plancha_config_path", default=None, help="Path to the plancha config file to use")


    return parser.parse_args()

def main(opt): 
    print_plancha_header()

    # Open json file with config of the session
    default_plancha_config = opt.plancha_config_path if opt.plancha_config_path != None else "./plancha_config/plancha_config.json"
    with open(default_plancha_config) as json_file:
        cfg_prog = json.load(json_file)

    # Override root path
    if opt.root_path:
        cfg_prog["session_info"]["root"] = opt.root_path

    # Saved default max depth
    default_max_depth = float(cfg_prog['bathy']['dpth_range']['max'])
    default_min_depth = float(cfg_prog['bathy']['dpth_range']['min'])


    # Build a list of [SESSION_NAME, FIRST_FRAME_UTC, FIRST_FRAME_NUMBER, filt_exclude_specific_timeUS, depth_range_max, depth_range_min]
    listSessionFirstFrame = [[
        cfg_prog['session_info']['session_name'], 
        str(cfg_prog['dcim']['time_first_frame_UTC']), 
        int(cfg_prog['dcim']['first_frame_to_keep']), 
        str(cfg_prog['gps']['filt_exclude_specific_timeUS']), 
        default_max_depth,
        default_min_depth
    ]]
    DEFAULT_SIZE = len(listSessionFirstFrame[0])
    if opt.csv != None and os.path.exists(opt.csv):
        with open(opt.csv, "r") as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',')
            header = next(spamreader, None)
            listSessionFirstFrame = [row if len(row) == DEFAULT_SIZE else row + [""] * (DEFAULT_SIZE - len(row)) for row in spamreader]

    ROOT = cfg_prog['session_info']['root']
    # list of config files to run (files should have .conf ext)
    ppk_cfgs = [cfg_prog['gps']['ppk_config_name']]
    PPK_CONFIG_PATH = cfg_prog['gps']['ppk_config_path']

    # if true, than do ppk with the basegps file and write the mean of the LLH position in the config file
    gpsbaseposition_mean_on_llh = cfg_prog['gps']['gpsbaseposition_mean_on_llh']

    # define frequence of frames
    frames_per_second = cfg_prog['dcim']['frames_per_second']
    a, b = [float(i) for i in frames_per_second.split('/')] if "/" in frames_per_second else (float(frames_per_second), 1)
    delta_time = str(1/(a/b))
    exiftool_config_path = cfg_prog['dcim']['exiftool_config_path']
    remove_frames_outside_mission = cfg_prog['dcim']['remove_frames_outside_mission']


    # for the leap second definition please refer to : https://fr.wikipedia.org/wiki/Synchronisation_GPS
    leap_sec = int(cfg_prog['dcim']['leap_sec'])
    # La Reunion only
    rgp_station = cfg_prog['gps']['rgp_station']
    # flag for filter on rtkfix data
    flag_rtkfix =  cfg_prog['gps']['filt_rtkfix']
    # flag for force rgp station
    cfg_prog['gps']['force_use_rgp'] = True if cfg_prog['gps']['force_use_rgp'] else opt.force_use_rgp

    # Init some variables to monitoring
    session_name_fails = []
    # Go over all file from session_csv
    for session_name, time_first_frame, number_first_frame, filt_exclude_specific_timeUS, depth_range_max, depth_range_min in listSessionFirstFrame:
        print("\n\n-- Launching " + session_name)

        try:
            # Change session_name in cfg_prog else we have bad name
            cfg_prog['session_info']['session_name'] = session_name 
            cfg_prog['dcim']['time_first_frame_UTC'] = time_first_frame
            cfg_prog['dcim']['first_frame_to_keep'] = int(opt.remove_frames) if opt.remove_frames and opt.remove_frames.isnumeric() else number_first_frame # Override

            # derived paths and parameters
            SESSION_PATH = os.path.join(ROOT, session_name)
            VIDEOS_PATH = os.path.join(SESSION_PATH, "DCIM")
            METADATA_PATH = os.path.join(SESSION_PATH, "METADATA")
            SENSORS_PATH = os.path.join(SESSION_PATH, "SENSORS")
            GPS_PATH = os.path.join(SESSION_PATH, "GPS")
            GPS_BASE_PATH = os.path.join(GPS_PATH, "BASE")
            GPS_DEVICE_PATH = os.path.join(GPS_PATH, "DEVICE")
        
            PROCESSED_PATH = os.path.join(SESSION_PATH, "PROCESSED_DATA")
            FRAMES_PATH = os.path.join(PROCESSED_PATH, "FRAMES")
            RELATIVE_PATH = os.path.join(session_name, "PROCESSED_DATA", "FRAMES")
            BATHY_PATH = os.path.join(PROCESSED_PATH, "BATHY")
            SESSION_INFO_PATH = os.path.join(METADATA_PATH, "session_info.csv")
            CSV_EXIFTOOL_FRAMES = os.path.join(METADATA_PATH, "metadata.csv")

            flag_gps = 0
            # N.B. insert the date and time following the format "YYYY:MM:DD HH:MM:SS.000"
            # N.B. insert the time in UTC+0 format
            # correct time by adding leap seconds to match GPS time (in 2023 it is 18 s)
            d_date = datetime.strptime(time_first_frame , '%Y:%m:%d %H:%M:%S.%f') + pd.Timedelta(seconds = leap_sec)
            time_first_frame = d_date.strftime('%Y:%m:%d %H:%M:%S.%f')


            ### Clean Processed session
            if cfg_prog['session_info']['delete_processed_session'] :
                frames_path = "" if "f" in opt.no_clean else FRAMES_PATH
                bathy_path = "" if "b" in opt.no_clean else BATHY_PATH
                meta_path = "" if "m" in opt.no_clean else METADATA_PATH
                gb_path = "" if "g" in opt.no_clean else GPS_BASE_PATH
                gd_path = "" if "g" in opt.no_clean else GPS_DEVICE_PATH
                clear_processed_session(frames_path, bathy_path, meta_path, gb_path, gd_path)
            
            ### Try to know if DCIM have just image
            isVideoOrImageOrNothing = get_dcim_type(VIDEOS_PATH)
            if isVideoOrImageOrNothing == 0: # Image
                FRAMES_PATH = VIDEOS_PATH
                RELATIVE_PATH = os.path.join(session_name, "DCIM")
                frames_per_second = get_frame_per_second_for_image(FRAMES_PATH)
                cfg_prog['dcim']['frames_per_second'] = str(frames_per_second)


            ### write metadata on session_info file
            write_session_info(SESSION_INFO_PATH, frames_per_second, time_first_frame, leap_sec)

            ### Split videos into frames
            if not opt.no_split and isVideoOrImageOrNothing == 1:
                split_videos(VIDEOS_PATH, FRAMES_PATH, frames_per_second, session_name)
            
            ### We just want to split videos so we continue
            if opt.only_split: continue
            
            ### Remove frames
            remove_first_frames(FRAMES_PATH, int(cfg_prog['dcim']['first_frame_to_keep']))

            ### Add specific filtering interval values
            if filt_exclude_specific_timeUS != "":
                cfg_prog['gps']['filt_exclude_specific_timeUS'] = json.loads(filt_exclude_specific_timeUS)
            else:
                cfg_prog['gps']['filt_exclude_specific_timeUS'] = []
            
            ### Max/Min depth
            cfg_prog['bathy']['dpth_range']['max'] = float(depth_range_max) if depth_range_max != "" else default_max_depth
            cfg_prog['bathy']['dpth_range']['min'] = float(depth_range_min) if depth_range_min != "" else default_min_depth

            
            ### Compute GPS file (either with ppk or not)
            if cfg_prog['gps']['use_llh_position'] == True:
                LLH_PATH, flag_gps = compute_gps(SESSION_INFO_PATH, GPS_DEVICE_PATH, GPS_BASE_PATH, session_name, time_first_frame, FRAMES_PATH, SENSORS_PATH, rgp_station, delta_time, PPK_CONFIG_PATH, ppk_cfgs, flag_rtkfix, gpsbaseposition_mean_on_llh, cfg_prog)
                ### plot GPS accuracy
                TXT_PATH = GPS_position_accuracy(SESSION_INFO_PATH, LLH_PATH, GPS_DEVICE_PATH, flag_rtkfix) if flag_gps else ""
            else:
                TXT_PATH, flag_gps = compute_gps_for_only_device(SESSION_INFO_PATH, GPS_DEVICE_PATH, flag_rtkfix)

            ### run bathy analysis if possible
            if not opt.no_bathy:
                try:
                    df_bathy = run_bathy_analysis(cfg_prog, BATHY_PATH, TXT_PATH, SENSORS_PATH, SESSION_INFO_PATH)
                    if len(df_bathy) != 0:
                        cfg_prog = run_bathy_postprocessing(df_bathy, cfg_prog, BATHY_PATH)                            
                
                except Exception:
                    print(traceback.format_exc(), end="\n\n")
                    
                    print("[ERROR] Something occur during bathy, continue to write metadata in images")


            ### compute and add metadata to frames
            if not opt.no_annotate:
                time_calibration_and_geotag(time_first_frame, frames_per_second, flag_gps, exiftool_config_path, remove_frames_outside_mission,
                                            RELATIVE_PATH, BATHY_PATH, FRAMES_PATH, VIDEOS_PATH, SESSION_INFO_PATH, CSV_EXIFTOOL_FRAMES, TXT_PATH)
        
        except Exception:
            # Print error
            print(traceback.format_exc(), end="\n\n")
            
            # Store sessions name
            session_name_fails.append(session_name)

            # Write error in file
            with open("error.log", "a") as file:
                file.writelines(traceback.format_exc())
        
        finally:
            # Always write config in METADATA folder
            print("\n-- Finally, save plancha_config.json\n")
            with open(Path(METADATA_PATH,'prog_config.json'), 'w') as fp:
                json.dump(cfg_prog, fp,indent=3)

    # Stat
    print("End of process. On {} sessions, {} fails. ".format(len(listSessionFirstFrame), len(session_name_fails)))
    if (len(session_name_fails)):
        [print("\t* " + session_name) for session_name in session_name_fails]

if __name__ == "__main__":
    opt = parse_option()
    main(opt)