import shutil
from pathlib import Path

from .ImageManager import ImageManager
from .enum.FolderType import FolderType

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

        # Manager.
        image_manager = ImageManager(self.dcim_path, self.pd_frames_path)


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
        for folder_to_create in [self.metadata_path, self.pd_frames_path, self.pd_bathy_path]:
            folder_to_create.mkdir(exist_ok=True, parents=True)


    def get_path_based_on_folder_type(self, folder_type: FolderType) -> Path:
        if folder_type == FolderType.METADATA: return self.metadata_path
        if folder_type == FolderType.FRAMES: return self.pd_frames_path
        if folder_type == FolderType.BATHY: return self.pd_bathy_path
    


