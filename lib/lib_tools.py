import os
import shutil
import pycountry
import subprocess
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from geopy.geocoders import Nominatim

def print_plancha_header():
    print("""
██████╗ ██╗      █████╗ ███╗   ██╗ ██████╗██╗  ██╗ █████╗ 
██╔══██╗██║     ██╔══██╗████╗  ██║██╔════╝██║  ██║██╔══██╗
██████╔╝██║     ███████║██╔██╗ ██║██║     ███████║███████║
██╔═══╝ ██║     ██╔══██║██║╚██╗██║██║     ██╔══██║██╔══██║
██║     ███████╗██║  ██║██║ ╚████║╚██████╗██║  ██║██║  ██║
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝
    """)

def clear_processed_session(frames_path, bathy_path, metadata_path, gps_base_path, gps_device_path) :
    print("-- We are deleting already processed session: ")
    
    # Clean, remove and create FRAMES, BATHY, METADATA folder
    for folder in list(filter(lambda x: x != "", [frames_path, bathy_path, metadata_path])):
        print("\t* Deleting " + folder)
        if os.path.exists(folder):
            for item in os.listdir(folder):
                os.remove(os.path.join(folder, item))
            os.rmdir(folder)
        os.mkdir(folder)

    # Clean this type of architecture for GPS folders
    # | a.zip         => keep
    # | a/            => delete
    # |   a.LLH       => delete
    # |   a.TXT       => delete
    # | b.txt         => delete
    # | b.zip         => keep
    # | b.gpx         => keep
        

    # Keep only zip or gpx file in GPS/BASE    
    if os.path.exists(gps_base_path):
        print("\t* Keeping only zip and gpx file in " + gps_base_path)
        for item in os.listdir(gps_base_path):
            item_path = os.path.join(gps_base_path, item)
            if os.path.isdir(item_path) :
                for subitem in os.listdir(item_path):
                    os.remove(os.path.join(item_path, subitem))
                os.rmdir(item_path)
            elif not(item.endswith(".zip") or item.endswith(".gpx")):
                os.remove(item_path)

    # Keep only zip file in GPS/DEVICE
    if os.path.exists(gps_device_path):
        print("\t* Keeping only zip and gpx file in " + gps_device_path)
        for item in os.listdir(gps_device_path):
            item_path = os.path.join(gps_device_path, item)
            if os.path.isdir(item_path) :
                for subitem in os.listdir(item_path):
                    os.remove(os.path.join(item_path, subitem))
                os.rmdir(item_path)
            elif not(item.endswith(".zip") or item.endswith(".gpx")):
                os.remove(item_path)


def create_new_session_folder(ORIGIN_ROOT, NEW_DEST_ROOT, SESSION_NAME, optional_place, session_name_device, flag_country_code):  

    # old path
    SESSION_PATH = ORIGIN_ROOT + SESSION_NAME
    VIDEOS_PATH = SESSION_PATH + "/DCIM/videos"
    IMAGES_PATH = SESSION_PATH + "/DCIM/images"
    GPS_PATH = SESSION_PATH + "/GPS"
    SENSORS_PATH = SESSION_PATH + "/SENSORS"
    
    if "session_" in SESSION_NAME :
        OLD_SESSION_NAME = SESSION_NAME
        #1.GET DATE IN STANDARD FORMAT
        # Get the session date from the session name
        session_date = SESSION_NAME.split("session_")[1][0:10]
        # Convert to date object
        session_date2 = datetime.strptime(session_date, "%Y_%m_%d")
        # Convert to required standard format
        session_name_date = session_date2.strftime("%Y%m%d")
        #2.GET COUNTRY CODE ISO ALPHA 3
        session_name_place = flag_country_code + optional_place
        # if we have more session in the same day, retrieve the session number
        session_nb = SESSION_NAME.split("_")[-1]
        SESSION_NAME = session_name_date + "_" + session_name_place + "_" + session_name_device
        if session_nb.isnumeric() :
            SESSION_NAME = session_name_date + "_" + session_name_place + "_" + session_name_device + "_" + session_nb

    # # Create new session folder
    NEW_SESSION_PATH = os.path.join(NEW_DEST_ROOT, SESSION_NAME)
    print("\n-- We are creating the new session folder : ", NEW_SESSION_PATH)
    if (not(os.path.exists(NEW_SESSION_PATH))):
        os.makedirs(NEW_SESSION_PATH)

    # Create new parent subfodlers or copy old files
    NEW_DCIM_PATH = os.path.join(NEW_SESSION_PATH, "DCIM")
    print("\t* Creating " + NEW_DCIM_PATH)
    if (not(os.path.exists(NEW_DCIM_PATH))):
        os.makedirs(NEW_DCIM_PATH)

    # Copy all the videos in the new session folder
    if os.path.exists(VIDEOS_PATH):
        print("\t* Copying video from " + VIDEOS_PATH)
        files = os.listdir(VIDEOS_PATH)
        for item in tqdm(files):
            old_video_path = os.path.join(VIDEOS_PATH, item)
            if os.path.isfile(old_video_path):
                new_video_path = os.path.join(NEW_DCIM_PATH, item)
                shutil.copy(old_video_path, new_video_path)
    if os.path.exists(IMAGES_PATH):
        print("\t* Copying images from " + IMAGES_PATH)
        shutil.copytree(IMAGES_PATH, NEW_DCIM_PATH, dirs_exist_ok=True)
    
    # GPS
    NEW_GPS_PATH = os.path.join(NEW_SESSION_PATH, "GPS")
    print("\t* Creating " + NEW_GPS_PATH)
    if os.path.exists(GPS_PATH):
        shutil.copytree(GPS_PATH, NEW_GPS_PATH)
        # for item in tqdm(os.listdir(GPS_PATH)):
        #     if item.endswith(".zip"):
        #         old_gps_path = os.path.join(GPS_PATH, item)
        #         new_gps_path = os.path.join(NEW_GPS_PATH, item)
        #         shutil.copy(old_gps_path, new_gps_path)
    else:
        os.makedirs(NEW_GPS_PATH)


    # SENSORS
    NEW_SENSORS_PATH = os.path.join(NEW_SESSION_PATH, "SENSORS")
    print("\t* Creating " + NEW_SENSORS_PATH)
    if os.path.exists(SENSORS_PATH):
        shutil.copytree(SENSORS_PATH, NEW_SENSORS_PATH)
    else :
        os.makedirs(NEW_SENSORS_PATH)

    # METADATA
    NEW_METADATA_PATH = os.path.join(NEW_SESSION_PATH, "METADATA")
    print("\t* Creating " + NEW_METADATA_PATH)
    if not(os.path.exists(NEW_METADATA_PATH)):
        os.makedirs(NEW_METADATA_PATH)

    # PROCESSED_DATA
    NEW_PROCESSED_PATH = os.path.join(NEW_SESSION_PATH, "PROCESSED_DATA")
    print("\t* Creating " + NEW_PROCESSED_PATH)
    if (not(os.path.exists(NEW_PROCESSED_PATH))):
        os.makedirs(NEW_PROCESSED_PATH)
    folder_to_create = ["BATHY", "FRAMES"] # ["BATHY", "FRAMES", "IA", "PHOTOGRAMMETRY"]
    for folder in folder_to_create:
        path = os.path.join(NEW_PROCESSED_PATH, folder)
        if (not(os.path.exists(path))):
            os.makedirs(path)

    print("   Deleting: OK", end="\n\n")
    os.system('spd-say "The copy of the files is done"')

# !FIXME Useless fonction
def get_alpha_3_code_from_latlon(lat, lon) :

    # 1.get country code alpha_2 from https://nominatim.openstreetmap.org/ui/search.html 
    # (better than pycountry that returns Comoros from a position in Aldabra->Seychelles)
    geolocator = Nominatim(user_agent="foo_bar")
    coordinates = (lat, lon)
    location = geolocator.reverse(coordinates, exactly_one=True)
    country = location.address.split(',')[-1]  # type: ignore -- suppress error from pylance
    country_code_alpha_2 = location.raw["address"]["country_code"] # type: ignore -- suppress error from pylance

    #2.get country name from country code alpha_2
    country = pycountry.countries.get(alpha_2=country_code_alpha_2)
    country_name = country.name

    #3.get alpha_3 code from country name
    #dict of country alpha3 codes
    countries_code_alpha_3 = {}
    for country in pycountry.countries:
        countries_code_alpha_3[country.name] = country.alpha_3
    country_code_alpha_3 = countries_code_alpha_3[country_name]
    return country_code_alpha_3

def replace_comma_by_dot(file_path):
    with open(file_path, 'r+') as f:
        # Get all lines
        lines = [line.replace(',', '.') for line in f]

        # Move cursor to the start and writes all lines
        f.seek(0)
        f.writelines(lines)

def replace_line(file_name, line_num, text):
    with open(file_name, 'r+') as f:
        lines = f.readlines()
        lines[line_num] = text
        f.seek(0)
        f.writelines(lines)

def llh_to_txt(llh_path) :
    # Inputs :
    # 1.llh_path = path of the llh file 
    
    # Outputs :
    # 1.txt_path = path of the txt file, which can be used by exiftool functions
    # The function saves a txt file with the same information of the LLH file in the same directory

    # Get LLh file name and replace .LLH by .txt
    llh_file_name = os.path.basename(os.path.normpath(llh_path))
    txt_file_name = llh_file_name.replace("LLH", "txt")
    txt_path = llh_path.replace(llh_file_name, txt_file_name)

    with open(llh_path, "r") as f:
        with open(txt_path, "w") as newf:
            # Write LLH header
            newf.write("GPSDateStamp,GPSTimeStamp,GPSLatitude,GPSLongitude,elevation,fix,nbsat,sdn,sde,sdu,sdne,sdeu,sdun,age,ratio \n") # write new content at the beginning
            
            # Copying each line and replacing space separation by comma
            for line in f:
                line = ','.join(list(filter(lambda x : x != "", line.split(' '))))
                newf.write(line)
    
    return txt_path

def pos_to_llh(pos_path) :
    # Inputs :
    # 1.pos_path = path of the pos file 
    
    # Outputs :
    # 1.llh_path = path of the llh file 
    # The function saves a LLH file with the same information of the pos file in the same directory
    
    # get POS file name and replace .pos by .LLH
    pos_file_name = os.path.basename(os.path.normpath(pos_path))
    llh_file_name = pos_file_name.replace("pos", "LLH")
    llh_path = pos_path.replace(pos_file_name, llh_file_name)

    # open POS file 
    with open(pos_path, 'r') as f:
        # open txt file
        with open(llh_path, 'w') as newf:
            new_lines = [line for line in f if line.startswith("%") == False]
            newf.writelines(new_lines)

    return llh_path

def gpx_to_llh(gpx_path):
    # Inputs :
    # 1.filename = path to gpx_file 
    
    # Outputs :
    # The function saves a LLH file and a txt file with the same information of the gpx file in the same directory
    data = []
    header = "GPSDateStamp,GPSTimeStamp,GPSLatitude,GPSLongitude,elevation,fix,nbsat,sdn,sde,sdu,sdne,sdeu,sdun,age,ratio".split(',')
    with open(gpx_path, "r") as file:
        lat, lon, date, time = None, None, None, None
        waitingTime = False
        for row in file:
            row = row.replace("\n", "")

            if not waitingTime and "<trkpt" in row:
                waitingTime = True
                lat = float(row.split(" ")[-2].replace('lat="', '').replace('"', ''))
                lon = float(row.split(" ")[-1].replace('lon="', '').replace('">', ''))
            elif waitingTime and "<time>" in row:
                waitingTime = False
                date = row.split("T")[0].split(">")[1].replace("-", "/")
                time = row.split("T")[1].split("Z")[0]
                data.append((date, time, lat, lon))
            
    # Build dataframe
    df = pd.DataFrame(data, columns=header[0:4])
    for a in header[4:]:
        df[a] = 5 if a == "fix" else 0.0
    
    folder = Path(gpx_path).parent
    # Save llh.txt
    date, time, _, _ = data[0]
    FILENAME_TXT = f"{date.replace('/', '')}{time.replace(':', '').split('.')[0]}.txt"
    df.to_csv(Path(folder, FILENAME_TXT), index=False)

    # Save llh.LLH
    FILENAME_LLH = FILENAME_TXT.replace(".txt", ".LLH")
    df.to_csv(Path(folder, FILENAME_LLH), index=False, sep=" ", header=False)


def get_hours_from_bin_sensors(sensor_path):
    print("Get hours from bin sensors: ")
    if not os.path.exists(sensor_path): return 0, 0

    filebuf = './tmp.csv'
    for file in os.listdir(sensor_path):
        if file.endswith(".BIN"):
            file_path = os.path.join(sensor_path, file)

            # Parse bin.
            tmp_cmd = "python lib/mavlogdump.py --planner --format csv --type GPS "+file_path+" > "+filebuf
            subprocess.call(tmp_cmd, shell=True)

            # Read csv and remove file buffer.
            df = pd.read_csv(filebuf, sep=";")
            os.remove(filebuf)

            # Parse timestamp.
            first_hour = datetime.fromtimestamp(df.timestamp[0]).hour - 4
            last_hour = datetime.fromtimestamp(df.timestamp[len(df)-1]).hour + 1 - 4 #!FIXME Horrible, Manually put time offset from utc
            print("Hours found: ", first_hour, last_hour)
            return first_hour, last_hour
    return 0, 0