from pathlib import Path
from argparse import Namespace

from .ConfigManager import ConfigManager

class SessionBase:

    def __init__(self, opt: Namespace):
        
        self.config = ConfigManager(opt)
        self.session = self.config.get_session_path()

        # Folder.
        self.video_path = Path(self.session, "DCIM")
        self.metadata_path = Path(self.session, "METADATA") 
        self.sensors_path = Path(self.session, "SENSORS") 
        self.gps_base_path = Path(self.session, "GPS", "BASE") 
        self.gps_device_path = Path(self.session, "GPS", "DEVICE") 
        self.pd_bathy_path = Path(self.session, "PROCESSED_DATA", "BATHY")
        self.pd_frames_path = Path(self.session, "PROCESSED_DATA", "FRAMES") 

        # Important files.


