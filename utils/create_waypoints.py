"""

    Create a waypoints file from a BIN file.

    QGC WPL <VERSION>
    <INDEX> <CURRENT WP> <COORD FRAME> <COMMAND> <PARAM1> <PARAM2> <PARAM3> <PARAM4> <PARAM5/X/LATITUDE> <PARAM6/Y/LONGITUDE> <PARAM7/Z/ALTITUDE> <AUTOCONTINUE>
"""

from pathlib import Path
import pandas as pd
import os
import subprocess
import traceback

def update_session(session):
    
    if not Path.exists(session):
        raise NameError("Session Not found")

    
    sensor_folder = Path(session, "SENSORS")
    if not Path.exists(sensor_folder):
        raise NameError("SENSORS folder not found")


    filebuf = './tmp.csv'
    for file in sensor_folder.iterdir():
        if file.suffix.upper() != ".BIN": continue

        tmp_cmd = "python ../lib/mavlogdump.py --planner --format csv --type CMD "+str(file)+" > "+filebuf
        subprocess.call(tmp_cmd, shell=True)
        df_cmd = pd.read_csv(filebuf, sep=";")

        # Read csv and remove file buffer.
        os.remove(filebuf)

        file_to_create = Path(sensor_folder, f"{session.name}_{file.stem}.waypoints")
        data = []

        for index, row in df_cmd.iterrows(): 
            data.append([
                index, 0, int(row.Frame), int(row.CId), 
                int(row.Prm1), int(row.Prm2), int(row.Prm3), int(row.Prm4), 
                row.Lat, row.Lng, row.Alt, 1
            ])

        d = pd.DataFrame(data)
        d.to_csv(file_to_create, sep="\t", index=False, header=False)

        with open(file_to_create, "r+") as file:
            content = file.read()
            file.seek(0,0)
            file.write("QGC WPL 110\n" + content)

def main():
    root_folders = [
        "/media/bioeos/F/202210_plancha_session",
        "/media/bioeos/E/202211_plancha_session",
        
        "/media/bioeos/F/202301-07_plancha_session",
        "/media/bioeos/F/202305_plancha_session",

        "/media/bioeos/E/202309_plancha_session",
        "/media/bioeos/E/202310_plancha_session",
        "/media/bioeos/D/202311_plancha_session",
        "/media/bioeos/D/202312_plancha_session",

        "/media/bioeos/F/202403_plancha_session",
        "/media/bioeos/F/202404_plancha_session",
    ]
    cpt = 0
    session_failed = []
    for root in root_folders:
        root = Path(root)
        if not Path.exists(root) or not root.is_dir():
            print(f"Root folders not found {root}")
            continue
        
        for session in root.iterdir():
            try:
                update_session(session)
            except:
                print(traceback.format_exc(), end="\n\n")
                session_failed.append(session_failed)
    
            cpt += 1
    # Stat
    print("End of process. On {} sessions, {} fails. ".format(cpt, len(session_failed)))
    if (len(session_failed)):
        [print("\t* " + session_name) for session_name in session_failed]

if __name__ == "__main__":
    update_session(Path("/home/bioeos/Documents/Bioeos/plancha-session/20231204_REU-TROUDEAU_ASV-2_01/"))