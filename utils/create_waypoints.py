"""

    Create a waypoints file from a BIN file.

    QGC WPL <VERSION>
    <INDEX> <CURRENT WP> <COORD FRAME> <COMMAND> <PARAM1> <PARAM2> <PARAM3> <PARAM4> <PARAM5/X/LATITUDE> <PARAM6/Y/LONGITUDE> <PARAM7/Z/ALTITUDE> <AUTOCONTINUE>
"""

from pathlib import Path
import pandas as pd
pd.set_option("display.precision", 20)
import os
import subprocess
import datetime as dt

def convert_GMS_GWk_to_UTC_time(gpsweek,gpsseconds,leapseconds=0):
    datetimeformat = "%Y-%m-%d %H:%M:%S.%f"
    epoch = dt.datetime.strptime("1980-01-06 00:00:00.000",datetimeformat)
    elapsed = dt.timedelta(days=int((gpsweek*7)),seconds=int(gpsseconds+leapseconds))
    return dt.datetime.strftime(epoch + elapsed,datetimeformat)

def main():

    session = Path("/media/bioeos/F/202404_plancha_session/20240419_REU-TROUDEAU_ASV-1_01/")
    
    if not Path.exists(session):
        print(f"Session Not found")
        return
    
    sensor_folder = Path(session, "SENSORS")
    if not Path.exists(sensor_folder):
        print(f"SENSORS folder not found")
        return

    filebuf = './tmp.csv'
    for file in sensor_folder.iterdir():
        if file.suffix != ".BIN": continue

        tmp_cmd = "python ../lib/mavlogdump.py --planner --format csv --type MSG "+str(file)+" > "+filebuf
        subprocess.call(tmp_cmd, shell=True)
        df_msg = pd.read_csv(filebuf, sep=";")

        tmp_cmd = "python ../lib/mavlogdump.py --planner --format csv --type GPS "+str(file)+" > "+filebuf
        subprocess.call(tmp_cmd, shell=True)
        df_gps = pd.read_csv(filebuf, sep=";")

        # Read csv and remove file buffer.
        os.remove(filebuf)

        idx = 0
        file_to_create = Path(sensor_folder, f"{session.name}_{file.stem}.waypoints")

        data = [["QGC WPL 110"]]
        data, wp_datetime = [], []

        for _, row in df_msg.iterrows():
            if "WP" in row.Message :
                a = df_gps[df_gps["timestamp"] <= row["timestamp"]].iloc[-1]
                b = df_gps[df_gps["timestamp"] >= row["timestamp"]].iloc[0]
                lat = (a["Lat"] + b["Lat"]) / 2
                lon = (a["Lng"] + b["Lng"]) / 2

                data.append([idx, 0, 3, 16, 0, 0, 0, 0, lat, lon, 100, 1])
                idx += 1

                wp_datetime.append(convert_GMS_GWk_to_UTC_time(a.GWk,a.GMS/1000.0))
            
            elif "SetCamTrigDst" in row.Message:
                data.append([idx, 0, 0, 206, 0, 0, 1, 0, 0, 0, 0, 1])
                idx += 1

        start_wp, end_wp = wp_datetime[0], wp_datetime[-1]        
        d = pd.DataFrame(data)
        d.to_csv(file_to_create, sep="\t", index=False, header=False)

        with open(file_to_create, "r+") as file:
            content = file.read()
            file.seek(0,0)
            file.write("QGC WPL 110\n" + content)


if __name__ == "__main__":
    main()