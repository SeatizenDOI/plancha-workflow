"""
    Update time first frame for each session in prog_config.json
"""
from pathlib import Path
import json

ROOT_FOLDER = [
    "/media/bioeos/F/202210_plancha_session",
    "/media/bioeos/E/202211_plancha_session",
    "/media/bioeos/E/202301-07_plancha_session",
    "/media/bioeos/E/202309_plancha_session",
    "/media/bioeos/E/202310_plancha_session",
    "/media/bioeos/D/202311_plancha_session", 
    "/media/bioeos/D/202312_plancha_session"
]

session_by_name = {}
for file in Path(Path.cwd(), "../csv").iterdir():
    if not Path.exists(file):
        continue

    with open(file, "r") as f:
        for row in f:
            row = row.replace("\n", "").split(',')
            session_by_name[row[0]] = row[1:]


for path_root in ROOT_FOLDER:
    path_root = Path(path_root)
    for session in path_root.iterdir():
        path_session_config = Path(path_root, session, "PROCESSED_DATA/BATHY/prog_config.json")
        
        # If no config file, continue
        if not Path.exists(path_session_config):
            print(f"Path not found for {path_session_config}")
            continue
        
        try:
            session_val = session_by_name[session.name]
        except KeyError as k:
            print(f"No csv data found for session {session.name}")
            continue
        
        first_frame_number = session_val[1]
        time_first_frame = session_val[0] if first_frame_number != '0' else ""

        # Open json file with config of the session
        with open(path_session_config) as json_file:
            cfg_prog = json.load(json_file)
        
        cfg_prog["dcim"]["time_first_frame_UTC"] = time_first_frame

        # Dump values
        with open(path_session_config, 'w') as fp:
            json.dump(cfg_prog, fp,indent=3)