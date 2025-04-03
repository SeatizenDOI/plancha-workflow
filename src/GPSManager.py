import zipfile
from pathlib import Path


class GPSManager:

    def __init__(self, device_path: Path, base_path: Path) -> None:
        
        self.device_path = device_path
        self.base_path = base_path



    def setup(self) -> None:    
        """ Search and extract LLH file and RINEX"""

        # For each file in device 
        # Try to find llh file for device.
        # Try to find rinex file for device.

        # 
        # Device.
        for file in self.device_path.iterdir():
            if file.suffix.lower() != ".zip": continue
            
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(Path(file.parent, file.stem))
        
        # Base.
        for file in self.base_path.iterdir():
            if file.suffix.lower() != ".zip": continue
            
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(Path(file.parent, file.stem))