"""
# On parcourt chaque session, et pour chaque session, on établit un bilan de 

    # -- Vérification des paramètres gps.
        # On vérifie si on a un fichier _ppk.pos
            # S'il y en a un, ça veut dire que du ppk a été fait donc on regarde dans le dossier de base pour s'il y a un fichier _merged.o si oui => RGP s'il y a un RINEX et un LLH => BASE
            # Pour le ppk on essaie de savoir le pourcentage de Q1 et si la session a été filtré par rtkfilt.


        # S'il y a un fichier gpx => Juste gps from montre

        # Si juste llh => gps approximatif

    # Vérification de la bathy. On regarde s'il y a un fichier .BIN ou .LOG dans sensor et on regarde si il y a plus de 20 fichiers dans BATHY

    # On regarde s'il y a des vidéos

    # On regarde s'il y a des frames et si elles sont géorérencés

    # On regarde s'il y a des prédictions

"""

import traceback
import pandas as pd
from pathlib import Path
from exiftool import ExifToolHelper

OUTPUT_CSV = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/all_session_info.csv"

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

def readAndExtractPercentage(file):
    df = pd.read_csv(file, sep=",")
    if "fix" not in df or len(df) == 0: return 0, 0, 0

    q1 = round(len(df[df["fix"] == 1]) * 100 / len(df), 2)
    q2 = round(len(df[df["fix"] == 2]) * 100 / len(df), 2)
    q5 = round(len(df[df["fix"] == 5]) * 100 / len(df), 2)

    return q1, q2, q5

# Return percentage for Q1, Q2, Q5
def getPercentage(session, isPPK):
    gps_device_path = Path(session, "GPS", "DEVICE")
    if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
        print("\t\t[GPS ERROR] NO GPS DEVICE FOLDER")
        return 0,0,0
    
    for file in gps_device_path.iterdir():
        if isPPK and "ppk_solution" in file.name and ".txt" in file.name:
            return readAndExtractPercentage(file)
        elif not isPPK and "_LLH" in file.name and file.is_dir():
            for subfile in file.iterdir():
                if ".txt" in subfile.name:
                    return readAndExtractPercentage(subfile)
        elif not isPPK and ".txt" in file.name and Path.exists(Path(file.parent, file.name.replace(".txt", ".LLH"))):
            return readAndExtractPercentage(file)
    
    return 0, 0, 0

def getBaseType(session):
    gps_base_path = Path(session, "GPS", "BASE")
    if not Path.exists(gps_base_path) or not gps_base_path.is_dir():
        print("\t\t[GPS ERROR] NO GPS BASE FOLDER")
        return None
    
    # Check for merged.o
    for file in gps_base_path.iterdir():
        if "merged.o" in file.name:
            return "RGP"
    
    # Check for LLh
    for file in gps_base_path.iterdir():
        if "_RINEX" in file.name:
            return "BASE"
    
    return None

def check_gpx(session):
    gps_device_path = Path(session, "GPS", "DEVICE")
    if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
        print("\t\t[GPS ERROR] NO GPS DEVICE FOLDER")
        return False
    
    for file in gps_device_path.iterdir():
        if ".gpx" in file.name:
            return True
    return False

def checkSensorFile(session):
    sensor_path = Path(session, "SENSORS")
    if not Path.exists(sensor_path) or not sensor_path.is_dir():
        print("\t\t[SENSOR ERROR] NO SENSOR FOLDER")
        return False

    for file in sensor_path.iterdir():
        if ".bin" in file.name.lower() or ".log" in file.name.lower():
            return True
    return False

def getBathyStat(session):
    bathy_path = Path(session, "PROCESSED_DATA", "BATHY")
    if not Path.exists(bathy_path) or not bathy_path.is_dir():
        print("\t\t[BATHY ERROR] NO BATHY FOLDER")
        return False

    return len(list(bathy_path.iterdir())) > 20

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

def checkFrames(session):
    frames_path = Path(session, "PROCESSED_DATA", "FRAMES")
    if not Path.exists(frames_path) or not frames_path.is_dir():
        print("\t\t[FRAMES ERROR] NO FRAMES FOLDER")
        return 0, False

    nb_frames = len(list(frames_path.iterdir()))
    isGeoreferenced = False
    if nb_frames > 0:
        with ExifToolHelper() as et:
            metadata = et.get_metadata(next(frames_path.iterdir()))[0]
            if "Composite:GPSLongitude" in metadata and "Composite:GPSLatitude" in metadata:
                isGeoreferenced = True

    return nb_frames, isGeoreferenced

def getJacquesStat(session):
    IA_path = Path(session, "PROCESSED_DATA", "IA")
    if not Path.exists(IA_path) or not IA_path.is_dir():
        print("\t\t[IA ERROR] NO IA FOLDER")
        return "", 0, 0

    jacques_name, useful, useless = "", 0, 0
    for file in IA_path.iterdir():
        if "jacques" in file.name:
            jacques_name = file.name.split("_")[-1].replace(".csv", "")
            df = pd.read_csv(file)
            if len(df) > 0:
                useful = round(len(df[df["Useless"] == 0]) * 100 / len(df), 2)
                useless = round(len(df[df["Useless"] == 1]) * 100 / len(df), 2)
    
    return jacques_name, useful, useless

def getHuggingFace(session):
    IA_path = Path(session, "PROCESSED_DATA", "IA")
    if not Path.exists(IA_path) or not IA_path.is_dir():
        print("\t\t[IA ERROR] NO IA FOLDER")
        return ""
    
    for file in IA_path.iterdir():
        if "dino" in file.name:
            return file.name.replace(session.name + "_", "").replace(".csv", "")

    return ""

def main(root_folders):

    # Create csv
    headers = "Session,PPK,Base,GPXFile,Q1,Q2,Q5,SensorFile,BathySucceed,DCIM,FRAMES,Georeferenced,Jacques model,Useful,Useless,HuggingFace".split(',')
    data = []
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
            if not session_path.is_dir():
                print(f"\n\n[ERROR] Session {session_path} isn't a directory")
                continue

            print(f"\n-- \t Starting with {session}")

            try:
                # Find if we do ppk
                isPPK = check_ppk(session) 
                q1, q2, q5 = getPercentage(session, isPPK)
                basetype = getBaseType(session) if isPPK else None # 1 is Base station, 2 is RGP
                isGPX = check_gpx(session) # LLH from reach or LLH generated from gpx file (Garmin watch)


                # Check for bathy
                haveSensorFile = checkSensorFile(session)
                isBathyGenerated = getBathyStat(session)


                # Check for video
                isVideo = isVideoOrImages(session) # 0: Nothing, 1: MP4 files, 2: JPG files

                # Check for frames and georeferenced frames
                nb_frames, isGeoreferenced = checkFrames(session)

                # Check for predictions
                j_name, j_useful, j_useless = getJacquesStat(session)
                huggingface_name = getHuggingFace(session)
#                 print(f"PPK: {isPPK}, Q1: {q1}, Q2: {q2}, Q5: {q5}, Base type: {basetype} , isGPXFile: {isGPX}, Sensor File: {haveSensorFile}, BathySucceed: {isBathyGenerated}\n\
# DCIM fill with: {isVideo}, nb_frames: {nb_frames}, isGeoreferenced: {isGeoreferenced}, jacques: {j_name}, Useless: {j_useless}%, useful: {j_useful}%, huggingface_name: {huggingface_name} ")

                # Sumup all information
                data.append([session.name,isPPK, basetype, isGPX, q1,q2,q5,haveSensorFile, isBathyGenerated, isVideo, nb_frames, isGeoreferenced, j_name, j_useful, j_useless, huggingface_name])
            
            except Exception:
                # Print error
                print(traceback.format_exc(), end="\n\n")
                
                # Store sessions name
                session_name_fails.append(session.name)
        
        # Append blank line to csv
        data.append([])    
    
    df = pd.DataFrame(data, columns=headers)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"File generated to {OUTPUT_CSV}")

    # Stat
    print("End of process. On {} sessions, {} fails. ".format(session_number, len(session_name_fails)))
    if (len(session_name_fails)):
        [print("\t* " + session_name) for session_name in session_name_fails]

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