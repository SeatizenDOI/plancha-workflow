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

def replace_line(file_name: Path, line_num: int, text: str) -> None:
    with open(file_name, 'r+') as f:
        lines = f.readlines()
        lines[line_num] = text
        f.seek(0)
        f.writelines(lines)

def llh_to_txt(llh_path: Path) -> Path:
    # Inputs :
    # 1.llh_path = path of the llh file 
    
    # Outputs :
    # 1.txt_path = path of the txt file, which can be used by exiftool functions
    # The function saves a txt file with the same information of the LLH file in the same directory

    # Get LLh file name and replace .LLH by .txt
    txt_path = Path(llh_path.parent, f"{llh_path.stem}.txt")

    with open(llh_path, "r") as f:
        with open(txt_path, "w") as newf:
            # Write LLH header
            newf.write("GPSDateStamp,GPSTimeStamp,GPSLatitude,GPSLongitude,elevation,fix,nbsat,sdn,sde,sdu,sdne,sdeu,sdun,age,ratio \n") # write new content at the beginning
            
            # Copying each line and replacing space separation by comma
            for line in f:
                line = ','.join(list(filter(lambda x : x != "", line.split(' '))))
                newf.write(line)
    
    return txt_path

def pos_to_llh(pos_path: Path) -> Path:
    # Inputs :
    # 1.pos_path = path of the pos file 
    
    # Outputs :
    # 1.llh_path = path of the llh file 
    # The function saves a LLH file with the same information of the pos file in the same directory
    
    # get POS file name and replace .pos by .LLH
    llh_path = Path(pos_path.parent, f"{pos_path.stem}.LLH")

    # open POS file 
    with open(pos_path, 'r') as f:
        # open llh file
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


def get_hours_from_bin_sensors(session_name: str, sensors_path: Path) -> tuple[int, int]:
    print("Get hours from bin sensors: ")
    if not sensors_path.exists(): return 0, 0

    # Get utcoffset
    alpha3code = session_name.split("_")[1].split('-')[0] # Extract REU from 20230201_REU-STLEU_ASV-1_01
    alpha2code = pycountry.countries.get(alpha_3 = alpha3code).alpha_2
    utcoffset = dt.datetime.now(pytz.timezone(dict(pytz.country_timezones)[alpha2code][0])).utcoffset().seconds//3600

    filebuf = './tmp.csv'
    for file in sensors_path.iterdir():
        if file.suffix.lower() != ".bin": continue

        # Parse bin.
        tmp_cmd = "python src/lib/mavlogdump.py --planner --format csv --type GPS "+str(file)+" > "+filebuf
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


def convert_datetime_to_datetime_unix(dt_value_in_str: str) -> int:
    """ Convert string datetime utc in timestamp """
    return int(dt.datetime.strptime(dt_value_in_str, '%Y:%m:%d %H:%M:%S.%f').replace(tzinfo=dt.timezone.utc).timestamp() * 1e9)


def convert_datetime_unix_to_datetime(datetime_unix: int) -> str:
    """ Convert timestamp in string datetime utc """
    return dt.datetime.fromtimestamp(datetime_unix / 1e9, tz=dt.timezone.utc).strftime('%Y:%m:%d %H:%M:%S.%f')[:-3]