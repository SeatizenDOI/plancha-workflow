import shutil
import traceback
import pandas as pd
from pathlib import Path

from .GPSManager import GPSManager
from .ConfigManager import ConfigManager
from .ImageManager import ImageManager
from .enum.FolderType import FolderType

from .BathyManager import BathyManager
class SessionBase:

    def __init__(self, session_path: Path):
        
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


        # Check if we use llh_position:
        if not cm.use_llh_position():
            #! FIXME Add GPX
            self.gps_manager.GPS_position_accuracy(self.session_info_path, self.gps_manager.device_LLH_filepath, cm.is_rtkfix())
            self.gps_manager.ppk_solution = self.gps_manager.device_LLH_filepath
            return

        # Based on base GPS data, we try to figure out if we can do PPK.
        # If user want to perform PPK with RGP station or if rinex files are not here we need to download rgp data.
        if cm.force_rgp() or self.gps_manager.base_RINEX_filepath == None:
            print(f"Downloading RGP data from {cm.get_rgp_station()} station :")
            self.gps_manager.download_rgp(cm, self.session.name, self.pd_frames_path, self.sensors_path)
            cm.set_force_rgp(True)

        # Check if we can perform ppk.
        if self.gps_manager.can_perform_ppk():
            print("We can do PPK on our data !")
            self.gps_manager.ppk(cm, self.session.name)
        else:
            print("We cannot do PPK on our data at the moment !")
            self.gps_manager.ppk_solution = self.gps_manager.device_LLH_filepath

        # Get the final GPS file with or without PPK solution
        if self.gps_manager.ppk_solution != None:
            self.gps_manager.GPS_position_accuracy(self.session_info_path, self.gps_manager.ppk_solution, cm.is_rtkfix())
        else:
            print("We do not have a navigation file.")
    
    def compute_bathy(self, cm: ConfigManager) -> None:

        if not cm.compute_bathy(): return

        print("\n-- BATHY Computing \n")

        try:
            self.bathy_manager.load_data(cm)

            if self.bathy_manager.dont_have_log_file():
                print("\ninfo: We do not have a log file or bin file. Abort bathy processing")
                return

            self.bathy_manager.run_bathy_analysis(cm, self.session_info_path, self.gps_manager.get_navigation_file_in_text())
            
            if self.bathy_manager.cannot_perform_bathy_post_processing():
                return
            
            self.bathy_manager.run_bathy_postprocessing(cm)

        except Exception:
            print(traceback.format_exc(), end="\n\n")
                    
            print("[ERROR] Something occur during bathy, continue to write metadata in images")

        