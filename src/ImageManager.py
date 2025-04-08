import ffmpeg
import exiftool
import traceback
import pandas as pd
from pathlib import Path
from natsort import natsorted
from datetime import datetime

from .enum.DCIMType import DCIMType
from .ConfigManager import ConfigManager

VIDEO_EXTENSION = [".mp4"]
IMAGE_EXTENSION = [".jpg", ".jpeg"]

class ImageManager:

    def __init__(self, session_name: str, dcim_path: Path, frame_path: Path) -> None:
        
        self.session_name = session_name
        self.dcim_path = dcim_path
        self.frame_path = frame_path
        self.relative_file_path = Path(session_name, "PROCESSED_DATA", "FRAMES")

        self.dcim_type = DCIMType.VIDEO # Default value.
        

    def setup(self, cm: ConfigManager) -> None:
        
        self.compute_dcim_type()

        if self.dcim_type == DCIMType.IMAGE:
            self.frame_path = self.dcim_path
            self.relative_file_path = Path(cm.get_session_name(), "DCIM") # session_name/DCIM
            fps = self.get_frame_per_second_for_image()
            cm.set_frames_per_second(fps)


    def compute_dcim_type(self) -> None:
        """ Get dcim type based on dcim folder content.  """

        if not self.dcim_path.exists() or not self.dcim_path.is_dir() :
            raise NameError("The following path does not exist : ", self.dcim_path)
        
        list_files_in_video_path = natsorted(list(self.dcim_path.iterdir()))
        if len(list_files_in_video_path) == 0: 
            self.dcim_type = DCIMType.OTHER
            return

        is_only_frames = False
        for file in list_files_in_video_path:
            if file.suffix.lower() in VIDEO_EXTENSION: 
                self.dcim_type = DCIMType.VIDEO
                return
            if file.suffix.lower() in IMAGE_EXTENSION: is_only_frames = True
        
        self.dcim_type = DCIMType.IMAGE if is_only_frames else DCIMType.OTHER 
    

    def get_frame_per_second_for_image(self) -> str:
        """ Return str frame_per_second else 1 """
        self.frame_path = Path(self.frame_path)

        if not Path.exists(self.frame_path) or not self.frame_path.is_dir():
            raise NameError("The following path does not exist : ", self.frame_path)
        

        frame_per_second_str, fps = "", 1
        for file in self.frame_path.iterdir():
            if file.suffix.lower() not in IMAGE_EXTENSION: continue
            with exiftool.ExifToolHelper() as et:
                json_frame_metadata = et.get_metadata(file)[0]
            
                for key in (json_frame_metadata):
                    if "rate" in key.lower():
                        frame_per_second_str = json_frame_metadata[key]
                        break
            break
        if frame_per_second_str != "" and "SEC" in frame_per_second_str:
            a, b = [int(i) for i in frame_per_second_str.replace("SEC", "").split("_")]
            fps = a if a > b else a / b # 4_1SEC = 4fps and 1_2SEC = O.5fps
            
        return str(fps) 


    def dcim_folder_is_video_folder(self) -> bool:
        return self.dcim_type == DCIMType.VIDEO
    

    def split_videos(self, split_only_first_video: bool, fps: str) -> None:

        count_video = 0
        print("\n-- SPLITTING VIDEOS INTO FRAMES:")

        if len(list(self.frame_path.iterdir())) > 0: 
            print("Videos already split in frames")
            return        

        texec = datetime.now()
        # for each file in the videos folder
        for file in natsorted(list(self.dcim_path.iterdir())):
            if file.suffix.lower() not in VIDEO_EXTENSION: continue

            # increase the count video in order to differentiate between different videos of same session
            count_video += 1
            print("\t* We are treating the following file : ", file.name)

            # Define the ffmpeg command
            try:
                output_pattern = Path(self.frame_path, f"{self.session_name}_{count_video}_%03d.jpeg")  # Output pattern for the frames
                (
                    ffmpeg.input(str(file))
                    .output(str(output_pattern), vf=f'fps={fps}', qmin=1, q='1', loglevel='quiet') # Set output pattern, frame rate filter, quality parameters, and logging level
                    .run()  # Run the ffmpeg command
                )
            except Exception:
                print(traceback.format_exc(), end="\n\n")

            if split_only_first_video: break

        print(f"\nfunc: exec time --> {datetime.now() - texec} sec")
        print("End of splitting videos\n")
    
    
    def remove_first_frames(self, max_frames: int) -> None:
        if (max_frames <= 0): return

        print(f"-- Removing first frame")
        for frame in natsorted(list(self.frame_path.iterdir())):
            video_number, frame_number = [int(a) for a in frame.stem.split("_")[4:]]
            if max_frames < frame_number: break

            if video_number == 1 and frame_number < max_frames:
                print(f"Remove frame {frame}")
                frame.unlink()

            if video_number == 1 and max_frames == frame_number: break
    

    def remove_outside_frames(self, csv_exiftool_frames: pd.DataFrame, session_info: pd.DataFrame) -> pd.DataFrame:
        print("\n-- Remove frames before first waypoint and after last waypoint\n")

        if "Mission_START" not in list(session_info) or "Mission_END" not in list(session_info) or "SubSecDateTimeOriginal_np" not in csv_exiftool_frames:
            print("[WARNING] Mission interval wasn't found, no filtering.")
            return csv_exiftool_frames

        # Get unix_timestamp.
        start_wp = pd.to_datetime(session_info["Mission_START"].iloc[0])
        end_wp = pd.to_datetime(session_info["Mission_END"].iloc[0])

        # To avoid remove all frames on disfunction, we check if last frame is not before mission start or first frame after mission end.
        isAllFramesBeforeMissionStart = pd.to_datetime(csv_exiftool_frames["SubSecDateTimeOriginal_np"].iloc[-1]) < start_wp
        isAllFramesAfterMissionEnd = pd.to_datetime(csv_exiftool_frames["SubSecDateTimeOriginal_np"].iloc[0]) > end_wp

        if isAllFramesBeforeMissionStart or isAllFramesAfterMissionEnd: 
            print("func: Frames are not in mission interval, to avoid remove all frames, done nothing")
            return csv_exiftool_frames

        # Filter.
        csv_exiftool_frames = csv_exiftool_frames[pd.to_datetime(csv_exiftool_frames["SubSecDateTimeOriginal_np"]) >= start_wp]
        csv_exiftool_frames = csv_exiftool_frames[pd.to_datetime(csv_exiftool_frames["SubSecDateTimeOriginal_np"]) <= end_wp]

        list_frames, cpt_frames = list(csv_exiftool_frames["FileName"]), 0
        # Remove outside frames.
        for frame in self.frame_path.iterdir():
            if frame.name not in list_frames:
                cpt_frames += 1
                frame.unlink()
        print(f"func: {cpt_frames} frames have been deleted.")
        
        return csv_exiftool_frames


    def remove_frames_from_specific_intervals(self, csv_exiftool_frames: pd.DataFrame, filt_exclude_specific_datetimeUnix: list) -> pd.DataFrame:
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
        for frame in self.frame_path.iterdir():
            if frame.name not in list_frames:
                cpt_frames += 1
                frame.unlink()
        print(f"func: {cpt_frames} frames have been deleted.")
        
        return csv_exiftool_frames