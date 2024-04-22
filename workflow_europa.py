import json
import traceback
from pathlib import Path
from lib.lib_bathy import *

# FOLDER to treat
FOLDER = Path("/home/bioeos/Documents/Bioeos/europa_session")

# Open json file with config of the session
with open('./plancha_config_europa.json') as json_file:
    cfg_prog = json.load(json_file)


for session in sorted(list(FOLDER.iterdir())):
    print(f"\n\n Working in session {session.name}")
    # derived paths and parameters
    SENSORS_PATH = Path(session, "SENSORS")
    BATHY_PATH = Path(session, "PROCESSED_DATA/BATHY")

    try:

        df_bathy = run_bathy_analysis(cfg_prog, str(BATHY_PATH), "", str(SENSORS_PATH))
        run_bathy_postprocessing(df_bathy, cfg_prog, str(BATHY_PATH))
    
    except Exception:
        # Print error
        print(traceback.format_exc(), end="\n\n")