import json
import shutil
import exiftool
import traceback
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from .GPSManager import GPSManager
from .BathyManager import BathyManager
from .ConfigManager import ConfigManager
from .ImageManager import ImageManager, VIDEO_EXTENSION

from .enum.DCIMType import DCIMType
from .enum.FolderType import FolderType

from .lib.lib_bathy import bathy_preproc_to_txt
from .lib.lib_tools import convert_datetime_to_datetime_unix, convert_datetime_unix_to_datetime

class SessionBase:

    def __init__(self, session_path: Path) -> None:
        
        self.session = Path(session_path)

        # Folder.
        self.dcim_path = Path(self.session, "DCIM")
        self.metadata_path = Path(self.session, "METADATA") 
        self.sensors_path = Path(self.session, "SENSORS") 
        self.gps_base_path = Path(self.session, "GPS", "BASE") 
        self.gps_device_path = Path(self.session, "GPS", "DEVICE") 
        self.pd_bathy_path = Path(self.session, "PROCESSED_DATA", "BATHY")
        self.pd_frames_path = Path(self.session, "PROCESSED_DATA", "FRAMES") 

        # Important files.
        self.prog_config_path = Path(self.metadata_path, "prog_config.json")
        self.session_info_path = Path(self.metadata_path, "session_info.csv")
        self.metadata_csv_path = Path(self.metadata_path, "metadata.csv")

        # Manager.
        self.image_manager = ImageManager(self.session.name, self.dcim_path, self.pd_frames_path)
        self.gps_manager = GPSManager(self.gps_device_path, self.gps_base_path)
        self.bathy_manager = BathyManager(self.sensors_path, self.pd_bathy_path)


    def prepare_folder(self, folder_to_clean: list[FolderType]) -> None:

        print("-- We are deleting already processed session: ")

        for ft in folder_to_clean:
            print("\t* Deleting " + ft.name)
            if ft == FolderType.GPS:
                # Clean this type of architecture for GPS folders
                # | a.zip         => keep
                # | a/            => delete
                # |   a.LLH       => delete
                # |   a.TXT       => delete
                # | b.txt         => delete
                # | b.zip         => keep
                # | b.gpx         => keep

                if self.gps_base_path.exists():
                    for file in self.gps_base_path.iterdir():
                        if file.suffix.lower() in [".zip", ".gpx"]: continue

                        if file.is_dir(): shutil.rmtree(file)
                        elif file.is_file(): file.unlink()
                
                if self.gps_device_path.exists():
                    for file in self.gps_device_path.iterdir():
                        if file.suffix.lower() in [".zip", ".gpx"]: continue

                        if file.is_dir(): shutil.rmtree(file)
                        elif file.is_file(): file.unlink()
  
            else:
                folder_to_remove = self.get_path_based_on_folder_type(ft)
                if folder_to_remove.exists():
                    shutil.rmtree(folder_to_remove)

        # Create folder.
        # To avoid next error, we create SENSORS and DCIM folder.
        for folder_to_create in [self.metadata_path, self.pd_frames_path, self.pd_bathy_path, self.sensors_path, self.dcim_path]:
            folder_to_create.mkdir(exist_ok=True, parents=True)


    def get_path_based_on_folder_type(self, folder_type: FolderType) -> Path:
        if folder_type == FolderType.METADATA: return self.metadata_path
        if folder_type == FolderType.FRAMES: return self.pd_frames_path
        if folder_type == FolderType.BATHY: return self.pd_bathy_path
    

    def write_session_info(self, cm: ConfigManager) -> None:
        print("\n-- Writing session info in csv file\n")

        session_info = pd.DataFrame({
            'frames_per_second': [cm.get_frames_per_second()], 
            'leap_sec': [cm.get_leap_second()],
            'time_first_frame': [cm.get_time_first_frame()] 
        })

        session_info.to_csv(self.session_info_path, index=False)
     

    def split_videos(self, cm: ConfigManager) -> None:
        
        if not cm.can_split() or not self.image_manager.dcim_folder_is_video_folder() : return 
        self.image_manager.split_videos(cm.is_only_split(), cm.get_frames_per_second())
    

    def remove_first_frames(self, cm: ConfigManager) -> None:

        max_frame = cm.get_first_frame_to_keep()
        self.image_manager.remove_first_frames(max_frame)


    def compute_gps(self, cm: ConfigManager) -> None:

        print("\n-- GPS Computing \n")

        if not self.gps_manager.need_compute_gps(): return

        self.gps_manager.setup(cm, self.session_info_path)

        try:

            # Check if we use llh_position:
            if not cm.use_llh_position():
                self.gps_manager.compute_gps_for_only_device()

            # Based on base GPS data, we try to figure out if we can do PPK.
            # If user want to perform PPK with RGP station or if rinex files are not here we need to download rgp data.
            elif cm.force_rgp() or self.gps_manager.base_RINEX_filepath == None:
                print(f"Downloading RGP data from {cm.get_rgp_station()} station :")
                self.gps_manager.download_rgp(cm, self.session.name, self.pd_frames_path, self.sensors_path)
                cm.set_force_rgp(True)

            # Check if we can perform ppk.
            if self.gps_manager.can_perform_ppk():
                print("We can do PPK on our data !")
                self.gps_manager.ppk(cm, self.session.name)
            else:
                print("We cannot do PPK on our data at the moment !")

            if self.gps_manager.ppk_solution == None:
                self.gps_manager.ppk_solution = self.gps_manager.device_LLH_filepath

            # Get the final GPS file with or without PPK solution
            if self.gps_manager.ppk_solution != None:
                self.gps_manager.GPS_position_accuracy(self.session_info_path, self.gps_manager.ppk_solution, cm.is_rtkfix())
            else:
                raise NameError("No Navigation where found.")

        except:
            print(traceback.format_exc(), end="\n\n")
            print('\n--- WARNING ---')
            print('Problem occurs when trying to process GPS ...')
        print('Done ...')
    
    def compute_bathy(self, cm: ConfigManager) -> None:

        if not cm.compute_bathy(): return

        print("\n-- BATHY Computing \n")

        try:
            self.bathy_manager.load_data(cm)

            if self.bathy_manager.dont_have_log_file():
                print("\ninfo: We do not have a log file or bin file. Abort bathy processing")
                return

            self.bathy_manager.run_bathy_analysis(cm, self.session_info_path, self.gps_manager.get_navigation_file_in_text())
            
            if self.bathy_manager.cannot_perform_bathy_post_processing(): return
            
            self.bathy_manager.run_bathy_postprocessing(cm)

        except Exception:
            print(traceback.format_exc(), end="\n\n")
                    
            print("[ERROR] Something occur during bathy, continue to write metadata in images")


    def update_filt_exclude_interval(self, cm: ConfigManager, filt_exclude_specific_datetimeUTC: str) -> None:

        filt_exclude_specific_datetimeUTC_list = [] if filt_exclude_specific_datetimeUTC == "" else json.loads(filt_exclude_specific_datetimeUTC.replace("'", '"'))
        datetimeUTC_to_datetimeUnix = [[convert_datetime_to_datetime_unix(a), convert_datetime_to_datetime_unix(b)] for a, b in filt_exclude_specific_datetimeUTC_list]
        self.bathy_manager.filt_exclude_specific_datetimeUnix += datetimeUTC_to_datetimeUnix
        filt_exclude_specific_datetimeUTC_list = [[convert_datetime_unix_to_datetime(a), convert_datetime_unix_to_datetime(b)] for a, b in self.bathy_manager.filt_exclude_specific_datetimeUnix]

        cm.set_filt_exclude_specific_datetimeUTC(filt_exclude_specific_datetimeUTC_list)
        
    
    def tags_frames(self, cm: ConfigManager) -> None:

        if cm.dont_tags_frames(): return

        # Get metadata of frames
        with exiftool.ExifTool(common_args=["-n"]) as et:
            json_frames_metadata = et.execute(*[f"-j", "-fileorder", "filename", str(self.image_manager.frame_path)])

        if json_frames_metadata == "":
            print("No frames to write metadata")
            return
        
        csv_exiftool_frames = pd.DataFrame.from_dict(json.loads(json_frames_metadata))

        # Get metadata of one video
        csv_exiftool_video = pd.DataFrame()
        if self.dcim_path != self.image_manager.frame_path:

            if not Path.exists(self.dcim_path) or not self.dcim_path.is_dir() :
                print("The following path does not exist : ", self.dcim_path)
                return
            
            file_path = None
            for file in self.dcim_path.iterdir():
                if file.suffix.lower() in VIDEO_EXTENSION: 
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
        session_info = pd.read_csv(self.session_info_path)
        session_info = pd.concat([session_info, csv_exiftool_video], axis=1)
        # remove empy and Nan columns
        nan_value = float("NaN")
        session_info.replace("", nan_value, inplace=True)
        session_info.dropna(how='all', axis=1, inplace=True)
        # save session_info df
        session_info.to_csv(self.session_info_path, sep = ',', index=False)
    
        print("\n-- ADD DATE AND TIME TO CSV METADATA\n")

        # convert "time_first_frame" to "time_first_frame_np" in order to create np vector of DateTime
        time_first_frame_np = cm.get_time_first_frame().replace(" ", "T")
        time_first_frame_np = time_first_frame_np.replace(":", "-", 2)
        # define time first frame in np format, step and nb of samples
        start = np.datetime64(time_first_frame_np, 'ns')
        # Handle fraction in frames_seconds => 2997/1000 : 2997, 1000 or 3 : 3.0, 1
        frames_per_second = cm.get_frames_per_second()
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
        if self.gps_manager.ppk_solution != None :
            print("\n-- ADD POSITION, ROLL, PITCH, YAW, DEPTH TO CSV METADATA\n")
            # convert "SubSecDateTimeOriginal_np" to unix time in order to do interpolation
            # please see : https://www.unixtimestamp.com/
            csv_exiftool_frames['datetime_unix'] = csv_exiftool_frames['SubSecDateTimeOriginal_np'].astype('int64')
            #############################
            # import lat and lon from LLH
            #############################
            csv_llh = pd.read_csv(self.gps_manager.get_navigation_file_in_text())
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

        for file in self.pd_bathy_path.iterdir():
            if "bathy_preproc.csv" == file.name:
                flag_bathy = 1
                csv_bathy_preproc_path = bathy_preproc_to_txt(file)

        if flag_bathy == 1 :
            ######################################################
            # import roll, pitch, yaw and depth from bathy_preproc
            ######################################################

            csv_bathy_preproc = pd.read_csv(csv_bathy_preproc_path)
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
        csv_exiftool_frames.to_csv(self.metadata_csv_path, index=False) 

        # Remove frames outside mission 
        if cm.should_I_remove_frames_outside_mission():
            csv_exiftool_frames = self.image_manager.remove_outside_frames(csv_exiftool_frames, session_info)

        # Remove frames if filt_exclude_specific_datetimeUnix
        if cm.should_I_remove_frames_outside_mission() and len(self.bathy_manager.filt_exclude_specific_datetimeUnix) != 0:
            csv_exiftool_frames = self.image_manager.remove_frames_from_specific_intervals(csv_exiftool_frames, self.bathy_manager.filt_exclude_specific_datetimeUnix)

        print("\n-- func : IMPORT EXIF METADATA\n")

        # Only write metadata for frames split by the code else conserve the exif of original images.
        if self.image_manager.dcim_type == DCIMType.VIDEO:
            texec = datetime.now()
            with exiftool.ExifTool(common_args=[], config_file=str(cm.get_exiftool_metadata_path())) as et:
                et.execute("-csv="+str(self.metadata_csv_path)," -fileorder filename", str(self.image_manager.frame_path), "-overwrite_original")
            print("Writing metadata execution time: ", datetime.now() - texec)

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
        
        # Rename images without the session_name inside
        def rename_image_if_needed(filename) -> str:
            if self.session.name in filename: return filename
            new_filename = f"{self.session.name}_{filename}"

            shutil.move(Path(self.image_manager.frame_path, filename), Path(self.image_manager.frame_path, new_filename))
            return new_filename
            
        csv_exiftool_frames["FileName"] = csv_exiftool_frames["FileName"].apply(lambda x : rename_image_if_needed(x))

        # add relative path
        csv_exiftool_frames["relative_file_path"] = csv_exiftool_frames["FileName"].apply(lambda x : str(Path(self.image_manager.relative_file_path, x)))
        # sort metadata columns by name
        csv_exiftool_frames = csv_exiftool_frames.sort_index(axis=1)
        # save filtered frame csv, after import metadata
        csv_exiftool_frames.to_csv(self.metadata_csv_path, index=False)