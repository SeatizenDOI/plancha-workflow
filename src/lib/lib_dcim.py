import os
import json
import ffmpeg
import exiftool
import traceback
import numpy as np
import pandas as pd
import datetime as dt
from pathlib import Path
from natsort import natsorted

from lib.lib_bathy import bathy_preproc_to_txt



def remove_frames_from_specific_intervals(csv_exiftool_frames, FRAMES_PATH, filt_exclude_specific_datetimeUnix):
    print("\n-- Remove frames on specfic interval \n")
    
    if "datetime_unix" not in csv_exiftool_frames:
        print("[WARNING] No column named datetime_unix.")
        return csv_exiftool_frames

    for f_start, f_stop in filt_exclude_specific_datetimeUnix:
        dfa = csv_exiftool_frames[csv_exiftool_frames["datetime_unix"] < f_start]
        dfb = csv_exiftool_frames[csv_exiftool_frames["datetime_unix"] > f_stop]
        csv_exiftool_frames = pd.concat([dfa, dfb])

    list_frames, cpt_frames = list(csv_exiftool_frames["FileName"]), 0
    # Remove outside frames.
    for frame in Path(FRAMES_PATH).iterdir():
        if frame.name not in list_frames:
            cpt_frames += 1
            frame.unlink()
    print(f"func: {cpt_frames} frames have been deleted.")
    
    return csv_exiftool_frames


def time_calibration_and_geotag(time_first_frame, frames_per_second, flag_gps, exiftool_config_path, remove_frames_outside_mission,
                                filt_exclude_specific_datetimeUnix,
                                RELATIVE_PATH, BATHY_PATH, FRAMES_PATH, VIDEOS_PATH, SESSION_INFO_PATH, CSV_EXIFTOOL_FRAMES, TXT_PATH):

    print("\n-- 3B of 6 : EXPORT VIDEO & FRAME METADATA TO CSV\n")

    # Get metadata of frames
    with exiftool.ExifTool(common_args=["-n"]) as et:
        json_frames_metadata = et.execute(*[f"-j", "-fileorder", "filename", FRAMES_PATH])

    if json_frames_metadata == "":
        print("No frames to write metadata")
        return
    
    csv_exiftool_frames = pd.DataFrame.from_dict(json.loads(json_frames_metadata))

    # Get metadata of one video
    csv_exiftool_video = pd.DataFrame()
    if VIDEOS_PATH != FRAMES_PATH:
        VIDEOS_PATH = Path(VIDEOS_PATH)
        if not Path.exists(VIDEOS_PATH) or not VIDEOS_PATH.is_dir() :
            print("The following path does not exist : ", VIDEOS_PATH)
            return
        
        file_path = None
        for file in VIDEOS_PATH.iterdir():
            if file.suffix.lower() == ".mp4": 
                file_path = file 
                break   

        if file_path == None:
            print(f"No video file found for extracting metadata")
        
        with exiftool.ExifToolHelper(common_args=[]) as et:
            metadata = et.get_metadata(file_path)

        csv_exiftool_video = pd.DataFrame(metadata)

        # filter video metadata
        useful_video_metadata_names =  ['LensSerialNumber', 'CameraSerialNumber', 'Model', 'AutoRotation', 'DigitalZoom', 'ProTune', 'WhiteBalance', 'Sharpness', 'ColorMode', 'MaximumShutterAngle', 'AutoISOMax', 'AutoISOMin', 'ExposureCompensation', 'Rate', 'FieldOfView', 'ElectronicImageStabilization', 'ImageWidth', 'ImageHeight', 'SourceImageHeight', 'XResolution', 'VideoFrameRate', 'ImageSize', 'Megapixels', 'AvgBitrate']
        video_col_names = csv_exiftool_video.columns
        video_intersection_list = list(set(video_col_names) & set(useful_video_metadata_names))
        csv_exiftool_video = csv_exiftool_video[video_intersection_list]
        useful_video_metadata_values = csv_exiftool_video.iloc[0]
        # write video's metadata to frame csv
        for i in range(len(video_intersection_list)):
            csv_exiftool_frames[video_intersection_list[i]] = useful_video_metadata_values.iloc[i]
    # concat session_info csv and csv_exiftool_video csv
    session_info = pd.read_csv(SESSION_INFO_PATH)
    session_info = pd.concat([session_info, csv_exiftool_video], axis=1)
    # remove empy and Nan columns
    nan_value = float("NaN")
    session_info.replace("", nan_value, inplace=True)
    session_info.dropna(how='all', axis=1, inplace=True)
    # save session_info df
    session_info.to_csv(SESSION_INFO_PATH, sep = ',', index=False)
 
    print("\n-- 4 of 6 : ADD DATE AND TIME TO CSV METADATA\n")

    # convert "time_first_frame" to "time_first_frame_np" in order to create np vector of DateTime
    time_first_frame_np = time_first_frame.replace(" ", "T")
    time_first_frame_np = time_first_frame_np.replace(":", "-", 2)
    # define time first frame in np format, step and nb of samples
    start = np.datetime64(time_first_frame_np, 'ns')
    # Handle fraction in frames_seconds => 2997/1000 : 2997, 1000 or 3 : 3.0, 1
    fps1, fps2 = [float(i) for i in frames_per_second.split('/')] if "/" in frames_per_second else (float(frames_per_second), 1.0)
    step = np.timedelta64(int(1/float(fps1/fps2)*1e9), "ns")
    nb_of_frames = csv_exiftool_frames.shape[0] 
    # create vector of dates and times
    datetime_vec_np = np.arange(0,nb_of_frames)*step+start
    datetime_vec = []
    # convert "datetime_vec_np" to "datetime_vec" in order to create vector of DateTime in Exiftool format
    for curr_datetime in datetime_vec_np :
        curr_datetime = str(curr_datetime)
        curr_datetime = curr_datetime.replace("T", " ")
        curr_datetime = curr_datetime.replace("-", ":", 2)
        datetime_vec.append(curr_datetime)
    csv_exiftool_frames["SubSecDateTimeOriginal"] = datetime_vec
    csv_exiftool_frames["SubSecDateTimeOriginal_np"] = datetime_vec_np

    # 1.GPS
    if flag_gps == 1 :
        print("\n-- 5 of 6 : ADD POSITION, ROLL, PITCH, YAW, DEPTH TO CSV METADATA\n")
        # convert "SubSecDateTimeOriginal_np" to unix time in order to do interpolation
        # please see : https://www.unixtimestamp.com/
        csv_exiftool_frames['datetime_unix'] = csv_exiftool_frames['SubSecDateTimeOriginal_np'].astype('int64')
        #############################
        # import lat and lon from LLH
        #############################
        csv_llh = pd.read_csv(TXT_PATH)
        # create datetime col
        csv_llh['SubSecDateTimeOriginal_np'] = csv_llh['GPSDateStamp'] + ' ' + csv_llh['GPSTimeStamp']
        # adapt format to the exiftool one
        csv_llh['SubSecDateTimeOriginal_np'] = csv_llh['SubSecDateTimeOriginal_np'].str.replace("/", "-")
        # convert column to date type (and express in "ms" to corresponds to csv_exiftool_frames["SubSecDateTimeOriginal_np"])
        csv_llh['SubSecDateTimeOriginal_np'] = pd.to_datetime(csv_llh['SubSecDateTimeOriginal_np'])
        csv_llh['datetime_unix'] = (csv_llh['SubSecDateTimeOriginal_np'] - pd.Timestamp("1970-01-01")) // pd.Timedelta("1ns")
        csv_llh['datetime_unix'] =  csv_llh['datetime_unix'].values.astype('int64')
        # linear interpolation, if different interpolation needed :
        # please see :
        # https://docs.scipy.org/doc/scipy/tutorial/interpolate/1D.html
        csv_exiftool_frames['GPSLatitude'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_llh['datetime_unix'], csv_llh['GPSLatitude'])
        csv_exiftool_frames['GPSLongitude'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_llh['datetime_unix'], csv_llh['GPSLongitude'])
        # A) we want to write lat and lon in "Composite" family tags, because in "Exif" family tags we cannot assign "-" sign to lat and lon
        #csv_exiftool_frames.rename(columns={"GPSLatitude": "Composite:GPSLatitude", "GPSLongitude": "Composite:GPSLongitude"}, inplace=True)
        # or B) Use fields Position and GPSxxxRef to specify coordinates
        csv_exiftool_frames['GPSPosition'] = [str(csv_exiftool_frames['GPSLatitude'][i])+', '+str(csv_exiftool_frames['GPSLongitude'][i]) for i in range(len(csv_exiftool_frames['GPSLatitude'] ))]
        # add STATUS (fix column, quality signal) and standars deviations to metadata.csv
        # please refer to pg.104:
        # https://www.rtklib.com/prog/manual_2.4.2.pdf
        csv_exiftool_frames['GPSfix'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_llh['datetime_unix'], csv_llh['fix'])
        # since we interpolate, we will have some decimal status values that does not have any sense
        # we assign to decimal values the worst case value following this rule :
        csv_exiftool_frames.loc[(csv_exiftool_frames['GPSfix']  > 1) & (csv_exiftool_frames['GPSfix']  < 2), 'GPSfix'] = 2
        csv_exiftool_frames.loc[(csv_exiftool_frames['GPSfix']  > 2) & (csv_exiftool_frames['GPSfix']  < 5), 'GPSfix'] = 5
        # add the mean square root of the absolute value of the estimated standard deviations of the solution assuming a priori
        # error model and error parameters by the positioning options.
        # The sdn, sde or sdu means N (north), E (east) or U (up) component of the standard deviations in m.
        # The absolute value of sdne, sdeu or sdun means square root of the absolute value of NE,
        # EU or UN component of the estimated covariance matrix.
        csv_exiftool_frames['GPSsdn'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_llh['datetime_unix'], csv_llh['sdn'])
        csv_exiftool_frames['GPSsde'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_llh['datetime_unix'], csv_llh['sde'])

    # 2.BATHY
    flag_bathy = 0
    # check if we have bathymetry data in order to add them to frames EXIF metadata
    if os.path.isdir(BATHY_PATH) :
        for file in os.listdir(BATHY_PATH):
            if file.endswith("bathy_preproc.csv"):
                flag_bathy = 1
                BATHY_PREPROC_PATH = BATHY_PATH + "/" + file
                CSV_BATHY_PREPOC = bathy_preproc_to_txt(BATHY_PREPROC_PATH)

    if flag_bathy == 1 :
        ######################################################
        # import roll, pitch, yaw and depth from bathy_preproc
        ######################################################

        csv_bathy_preproc = pd.read_csv(CSV_BATHY_PREPOC)
        # delete 3 last digit of "GPS_time"
        csv_bathy_preproc['GPS_time'] = csv_bathy_preproc['GPS_time'].str[:-3]
        # adapt format to the exiftool one
        csv_bathy_preproc['GPS_time'] = pd.to_datetime(csv_bathy_preproc['GPS_time'])
        csv_bathy_preproc['datetime_unix'] = (csv_bathy_preproc['GPS_time'] - pd.Timestamp("1970-01-01")) // pd.Timedelta("1ns")
        csv_bathy_preproc['datetime_unix'] = csv_bathy_preproc['datetime_unix'].values.astype('int64')

        # Before interpolate, we need to transform roll pitch yaw value if video was rotate. Ironically, video is rotate when autorotation value is Up
        if "AutoRotation" in csv_exiftool_video and csv_exiftool_video["AutoRotation"].iloc[0] == "Up":
            csv_bathy_preproc['GPSRoll'] *= -1
            csv_bathy_preproc['GPSPitch'] *= -1
            csv_bathy_preproc['GPSTrack'] = (csv_bathy_preproc['GPSTrack'] + 180) % 360

        csv_exiftool_frames['XMP:GPSRoll'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_bathy_preproc['datetime_unix'], csv_bathy_preproc['GPSRoll'])
        csv_exiftool_frames['XMP:GPSPitch'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_bathy_preproc['datetime_unix'], csv_bathy_preproc['GPSPitch'])
        csv_exiftool_frames['XMP:GPSTrack'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_bathy_preproc['datetime_unix'], csv_bathy_preproc['GPSTrack'])
        csv_exiftool_frames['GPSAltitude'] = np.interp(csv_exiftool_frames['datetime_unix'], csv_bathy_preproc['datetime_unix'], csv_bathy_preproc['GPSAltitude'])
        
        # set altitude below sea level
        csv_exiftool_frames['GPSAltitudeRef'] = "Below Sea Level"

    # add useful GoPro metadata
    if "FieldOfView" in csv_exiftool_frames and csv_exiftool_frames['FieldOfView'][0] == "Linear" :
        csv_exiftool_frames['EXIF:FocalLength'] = "2.92"
        csv_exiftool_frames["EXIF:FocalLengthIn35mmFormat"] = "15"
    
    # save frame csv, before import metadata
    csv_exiftool_frames.to_csv(CSV_EXIFTOOL_FRAMES, index=False) 

    # Remove frames outside mission 
    if remove_frames_outside_mission:
        csv_exiftool_frames = remove_outside_frames(csv_exiftool_frames, session_info, FRAMES_PATH)

    # Remove frames if filt_exclude_specific_datetimeUnix
    if remove_frames_outside_mission and len(filt_exclude_specific_datetimeUnix) != 0:
        csv_exiftool_frames = remove_frames_from_specific_intervals(csv_exiftool_frames, FRAMES_PATH, filt_exclude_specific_datetimeUnix)

    print("\n-- 6 of 6 : IMPORT EXIF METADATA\n")

    texec = dt.datetime.now()
    with exiftool.ExifTool(common_args=[], config_file=exiftool_config_path) as et:
        et.execute("-csv="+CSV_EXIFTOOL_FRAMES," -fileorder filename", FRAMES_PATH, "-overwrite_original")
    print("Writing metadata execution time: ", dt.datetime.now() - texec)

    # once we have imported all metadata, remove useless columns from metadata csv and rename GPS columns
    col_names = csv_exiftool_frames.columns
    # EXIF metadata we want to keep, please check :
    # https://docs.google.com/spreadsheets/d/1iSKDvFrh-kP9wOU9bt9H7lcZKOnF7pe9n-8t15pOrmw/edit?usp=sharing
    keep_param_list = ["ApertureValue", "Compression", "Contrast", "CreateDate", "DateCreated", "DateTimeDigitized", "DigitalZoomRatio", "ExifImageHeight", "ExifImageWidth", 
                        "ExifToolVersion", "ExifVersion", "ExposureCompensation", "ExposureMode", "ExposureProgram", "FileName", "FileSize", "FileType", "FileTypeExtension", "FNumber", 
                        "FocalLength", "FocalLength35efl", "FocalLengthIn35mmFormat", "FOV", "GPSAltitude", "GPSAltitudeRef", "GPSDateTime", "GPSDate", "GPSTime", "GPSLatitude", "GPSLongitude",
                        "GPSMapDatum", "GPSPosition", "GPSTimeStamp", "GPSRoll", "GPSPitch", "GPSTrack", "ImageHeight", "ImageWidth", "LightValue", "Make", "MaxApertureValue", 
                        "MaximumShutterAngle", "Megapixels", "MeteringMode", "MIMEType", "Model", "Saturation", "ScaleFactor35efl", "SceneCaptureType", "SceneType", "SensingMethod", "Sharpness", 
                        "ShutterSpeed", "Software", "SubSecDateTimeOriginal", "ThumbnailImage", "ThumbnailLength", "ThumbnailOffset", "WhiteBalance", "XResolution", "YResolution", "GPSfix", "GPSsdne", "GPSsde", "GPSsdn"]
    
    # intersection between metadata we want to keep and EXIF metadata
    intersection_list = []
    for col in col_names:
        col = col.split(':')[1] if ':' in col else col           
        if col in keep_param_list and col not in intersection_list:
            intersection_list.append(col)

    # Remove Exif: or XMP: in metadata.csv
    csv_exiftool_frames = csv_exiftool_frames.rename((lambda col : col.split(':')[1] if ':' in col else col), axis='columns') 
    # filter df
    csv_exiftool_frames = csv_exiftool_frames[intersection_list]
    # delete all empty columns
    csv_exiftool_frames.dropna(axis=1,inplace=True)
    # delete all zero columns
    csv_exiftool_frames = csv_exiftool_frames.loc[:, (csv_exiftool_frames != 0).any(axis=0)]
    # add relative path
    csv_exiftool_frames["relative_file_path"] = csv_exiftool_frames["FileName"].apply(lambda x : str(Path(RELATIVE_PATH, x)))
    # sort metadata columns by name
    csv_exiftool_frames = csv_exiftool_frames.sort_index(axis=1)
    # save filtered frame csv, after import metadata
    csv_exiftool_frames.to_csv(CSV_EXIFTOOL_FRAMES, index=False)