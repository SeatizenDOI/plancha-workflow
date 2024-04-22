from pathlib import Path
import os
import traceback
import shutil
import pandas as pd

FOLDER_SAVED_GPS = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/all_gps"

def isVideoOrImages(session):
    dcim_path = Path(session, "DCIM")
    if not Path.exists(dcim_path) or not dcim_path.is_dir():
        print("\t\t[DCIM ERROR] NO DCIM FOLDER")
        return None
    
    isVideoOrImagesOrNothing = None # None: Nothing, video: Video (priority), image: Images
    for file in dcim_path.iterdir():
        if ".mp4" in file.name.lower():
            return "video"
        if ".jpg" in file.name.lower() or ".jpeg" in file.name.lower():
            isVideoOrImagesOrNothing = "image"
    return isVideoOrImagesOrNothing

# Return True if ppk file else False
def check_ppk(session):
    gps_device_path = Path(session, "GPS", "DEVICE")
    if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
        print("\t\t[GPS ERROR] NO GPS DEVICE FOLDER")
        return False
    
    for file in gps_device_path.iterdir():
        filename = file.name
        if "ppk_solution" in filename and ".pos" in filename:
            return True
    return False

# Return percentage for Q1, Q2, Q5
def getGoodGPSFile(session):
    isPPK = check_ppk(session)
    gps_device_path = Path(session, "GPS", "DEVICE")
    if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
        print("\t\t[GPS ERROR] NO GPS DEVICE FOLDER")
        return ""
    
    for file in gps_device_path.iterdir():
        if isPPK and "ppk_solution" in file.name and ".txt" in file.name:
            return file
        elif not isPPK and "_LLH" in file.name and file.is_dir():
            for subfile in file.iterdir():
                if ".txt" in subfile.name:
                    return subfile
        elif not isPPK and ".txt" in file.name and Path.exists(Path(file.parent, file.name.replace(".txt", ".LLH"))):
            return file
    
    return ""


def main(root_folders):

    session_name_fails, session_number = [], 0
    for root_name in root_folders:
        
        # Get root folder
        root_folder = Path(root_folders[root_name])
        if not Path.exists(root_folder) or not root_folder.is_dir():
            print(f"\n\n[ERROR ROOT FOLDER] Cannot find root folder or root folder isn't a directory for: {root_folder}\n\n")
            continue
        
        for session_path in sorted(list(root_folder.iterdir())):
            session = Path(session_path)
            session_number += 1
            session_name = session.name
            if not session_path.is_dir():
                print(f"\n\n[ERROR] Session {session_path} isn't a directory")
                continue


            print(f"\n-- \t Starting with {session}")

            if len(session_name.split("_")) != 4 and len(session_name.split("_")) != 3:
                print(f"Session not split in 4 or 3 pieces for {session_name}")
                continue

            try:
                place = session_name.split("_")[1]
                opt_place = "".join(place.split("-")[1:])
                
                if isVideoOrImages(session) != "video":
                    print(f"Session {session_name} doesn't contain video")
                    continue

                file_to_copy = getGoodGPSFile(session)

                if file_to_copy == "":
                    print(f"GPS file not found for session {session_name}")
                    continue

                folder_to_move_gps = Path(FOLDER_SAVED_GPS, opt_place)
                if not Path.exists(folder_to_move_gps):
                    os.mkdir(folder_to_move_gps)
                
                shutil.copy(file_to_copy, Path(folder_to_move_gps, session_name+"_"+file_to_copy.name))

            except Exception:
                # Print error
                print(traceback.format_exc(), end="\n\n")
                
                # Store sessions name
                session_name_fails.append(session.name)
    
    # On merge tous les .txt
    for folder in Path(FOLDER_SAVED_GPS).iterdir():

        print(f"Working in {folder}")
        ad = [None]
        for file in folder.iterdir():
            df = pd.read_csv(file, sep=",")
            ad.append(df)
        df1 = pd.concat(ad)
        df1.to_csv(Path(folder, "merged.txt"), sep=",")



if __name__ == "__main__":

    root_folders = {
        "202210_plancha_session": "/media/bioeos/F/202210_plancha_session",
        "202301-07_plancha_session": "/media/bioeos/F/202301-07_plancha_session",
        "202305_plancha_session": "/media/bioeos/F/202305_plancha_session",

        # "2015_plancha_session": "/media/bioeos/E/2015_plancha_session",
        # "2021_plancha_session": "/media/bioeos/E/2021_plancha_session",
        "202211_plancha_session": "/media/bioeos/E/202211_plancha_session",
        "202309_plancha_session": "/media/bioeos/E/202309_plancha_session",
        "202310_plancha_session": "/media/bioeos/E/202310_plancha_session",

        "202311_plancha_session": "/media/bioeos/D/202311_plancha_session",
        "202312_plancha_session": "/media/bioeos/D/202312_plancha_session"
    }

main(root_folders)