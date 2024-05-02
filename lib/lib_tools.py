import os
import pytz
import pycountry
import subprocess
import pandas as pd
from pathlib import Path
import datetime as dt

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

def convert_GMS_GWk_to_UTC_time(gpsweek,gpsseconds,leapseconds=0):
    datetimeformat = "%Y-%m-%d %H:%M:%S.%f"
    epoch = dt.datetime.strptime("1980-01-06 00:00:00.000",datetimeformat)
    elapsed = dt.timedelta(days=int((gpsweek*7)),seconds=int(gpsseconds+leapseconds))
    return dt.datetime.strftime(epoch + elapsed,datetimeformat)

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
    print("func: Convert gpx file to llh file")
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


def get_hours_from_bin_sensors(SESSION_NAME, sensors_path):
    print("Get hours from bin sensors: ")
    if not os.path.exists(sensors_path): return 0, 0

    # Get utcoffset
    alpha3code = SESSION_NAME.split("_")[1].split('-')[0]
    alpha2code = pycountry.countries.get(alpha_3 = alpha3code).alpha_2
    utcoffset = dt.datetime.now(pytz.timezone(dict(pytz.country_timezones)[alpha2code][0])).utcoffset().seconds//3600

    filebuf = './tmp.csv'
    for file in os.listdir(sensors_path):
        if file.endswith(".BIN"):
            file_path = os.path.join(sensors_path, file)

            # Parse bin.
            tmp_cmd = "python lib/mavlogdump.py --planner --format csv --type GPS "+file_path+" > "+filebuf
            subprocess.call(tmp_cmd, shell=True)

            # Read csv and remove file buffer.
            df = pd.read_csv(filebuf, sep=";")
            os.remove(filebuf)

            # Parse timestamp.
            first_hour = dt.datetime.fromtimestamp(df.timestamp[0]).hour - utcoffset
            last_hour = dt.datetime.fromtimestamp(df.timestamp[len(df)-1]).hour + 1 - utcoffset
            print("Hours found: ", first_hour, last_hour)
            return first_hour, last_hour
    return 0, 0

def generate_theorique_waypoints_file(sensors_path, df_cmd):
    """
        Create a waypoints file from a BIN file.

        QGC WPL <VERSION>
        <INDEX> <CURRENT WP> <COORD FRAME> <COMMAND> <PARAM1> <PARAM2> <PARAM3> <PARAM4> <PARAM5/X/LATITUDE> <PARAM6/Y/LONGITUDE> <PARAM7/Z/ALTITUDE> <AUTOCONTINUE>
    """
    
    sensors_path = Path(sensors_path)
    file_to_create = Path(sensors_path, f"{sensors_path.parent.name}_mission.waypoints")
    data = []

    for index, row in df_cmd.iterrows():
        if index == 0: continue # Dismiss homepoint

        data.append([
            index-1, 0, int(row.Frame), int(row.CId), 
            int(row.Prm1), int(row.Prm2), int(row.Prm3), int(row.Prm4), 
            row.Lat, row.Lng, row.Alt, 1
        ])
    
    d = pd.DataFrame(data)
    d.to_csv(file_to_create, sep="\t", index=False, header=False)

    with open(file_to_create, "r+") as file:
        content = file.read()
        file.seek(0,0)
        file.write("QGC WPL 110\n" + content)

    return None, None

def write_real_mission_interval(SESSION_INFO_PATH, df_gps, df_msg):
    wp_datetime = []
    for _, row in df_msg.iterrows():
        if "Reached waypoint" not in row.Message: continue

        a = df_gps[df_gps["timestamp"] <= row["timestamp"]].iloc[-1] # Get the nearest gps position
        wp_datetime.append(convert_GMS_GWk_to_UTC_time(a.GWk,a.GMS/1000.0))

    if len(wp_datetime) == 0:
        print("func: Mission interval not found")
        return
    
    start_wp, end_wp = wp_datetime[0], wp_datetime[-1]

    # Write information in session_info
    session_info = pd.read_csv(SESSION_INFO_PATH)
    session_info.insert(len(session_info.columns), "Mission_START", [start_wp])
    session_info.insert(len(session_info.columns), "Mission_END", [end_wp])
    session_info.to_csv(SESSION_INFO_PATH, sep = ',', index=False)