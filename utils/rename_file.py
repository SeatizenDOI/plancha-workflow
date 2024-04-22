import os
import pandas as pd
from tqdm import tqdm
from pathlib import Path


ROOT_FOLDERS = ["/media/bioeos/F/202305_plancha_session"]
WORD_TO_FIND = "20231114_REU-SAINTLEU"
WORD_TO_WRITE = "20231114_REU-HERMITAGE"

def main ():
    for root_folder in ROOT_FOLDERS:
        print(f"We are in {root_folder} folder.")
        for session in tqdm(os.listdir(root_folder)):
            if WORD_TO_FIND not in session: continue # No need to rename

            # Rename session folder
            old_session_path = Path(root_folder, session)
            new_session_path = Path(root_folder, session.replace(WORD_TO_FIND, WORD_TO_WRITE))
            Path.rename(old_session_path, new_session_path)

            # Go to device gps et rename file
            gps_device_path = Path(new_session_path, "GPS/DEVICE")
            for file in os.listdir(gps_device_path):
                if WORD_TO_FIND in file:
                    old_file_path = Path(gps_device_path, file)
                    new_file_path = Path(gps_device_path, file.replace(WORD_TO_FIND, WORD_TO_WRITE))
                    Path.rename(old_file_path, new_file_path)

            # Go to processed data bathy and rename file
            bathy_path = Path(new_session_path, "PROCESSED_DATA/BATHY")
            for file in os.listdir(bathy_path):
                if WORD_TO_FIND in file:
                    old_file_path = Path(bathy_path, file)
                    new_file_path = Path(bathy_path, file.replace(WORD_TO_FIND, WORD_TO_WRITE))
                    Path.rename(old_file_path, new_file_path)

            # Go to frame folder and rename files
            frames_path = Path(new_session_path, "PROCESSED_DATA/FRAMES")
            for file in os.listdir(frames_path):
                if WORD_TO_FIND in file:
                    old_file_path = Path(frames_path, file)
                    new_file_path = Path(frames_path, file.replace(WORD_TO_FIND, WORD_TO_WRITE))
                    Path.rename(old_file_path, new_file_path)

            # go to metadata en open csv metadata and rename file
            metadata_file_path = Path(new_session_path, "METADATA/metadata.csv")
            if Path.exists(metadata_file_path):
                df = pd.read_csv(metadata_file_path)
                if "FileName" in df:
                    df['FileName'] = df['FileName'].str.replace(WORD_TO_FIND, WORD_TO_WRITE)
                df.to_csv(metadata_file_path, index=False)