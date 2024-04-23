import os
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime

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