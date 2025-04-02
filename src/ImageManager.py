from natsort import natsorted
from pathlib import Path

from .enum.DCIMType import DCIMType

class ImageManager:

    def __init__(self, dcim_path: Path, frame_path: Path):
        

        self.dcim_path = dcim_path
        self.frame_path = frame_path

        self.dcim_type = DCIMType.VIDEO # Default value.
        
        self.setup()
    

    def setup(self) -> None:
        
        self.dcim_type = self.get_dcim_type()



    def get_dcim_type(self) -> None:
        """ Get dcim type based on dcim folder content.  """

        if not self.dcim_path.exists() or not self.dcim_path.is_dir() :
            raise NameError("The following path does not exist : ", self.dcim_path)
        
        list_files_in_video_path = natsorted(list(self.dcim_path.iterdir()))
        if len(list_files_in_video_path) == 0: 
            self.dcim_type = DCIMType.OTHER
            return

        is_only_frames = False
        for file in list_files_in_video_path:
            if file.suffix.lower() in [".mp4"]: 
                self.dcim_type = DCIMType.VIDEO
                return
            if file.suffix.lower() in [".jpg", ".jpeg"]: is_only_frames = True
        
        self.dcim_type = DCIMType.IMAGE if is_only_frames else DCIMType.OTHER 