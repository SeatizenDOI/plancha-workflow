import enum
import pandas as pd
from pathlib import Path

class Sources(enum.Enum):
    CSV_SESSION = 0
    FOLDER = 1
    SESSION = 2

def get_mode_from_opt(opt) -> Sources:
    """ Retrive mode from input option """
    mode = None

    if opt.enable_csv: 
        mode = Sources.CSV_SESSION
    elif opt.enable_folder: 
        mode = Sources.FOLDER
    elif opt.enable_session: 
        mode = Sources.SESSION

    return mode

def get_src_from_mode(mode, opt) -> str:
    """ Retrieve src path from mode """
    src = ""

    if mode == Sources.CSV_SESSION:
        src = opt.path_csv_file
    elif mode == Sources.FOLDER:
        src = opt.path_folder
    elif mode == Sources.SESSION:
        src = opt.path_session

    return src

def get_list_sessions(opt) -> list:
    """ Retrieve list of sessions from input """

    list_sessions = []

    mode = get_mode_from_opt(opt)
    src = get_src_from_mode(mode, opt)

    if mode == Sources.SESSION:
        list_sessions = [src]

    elif mode == Sources.FOLDER:
        list_sessions = sorted(list(Path(src).iterdir()))
    
    elif mode == Sources.CSV_SESSION:
        src = Path(src)
        if Path.exists(src):
            df_ses = pd.read_csv(src)
            list_sessions = [str(Path(row.root_folder, row.session_name)) for row in df_ses.itertuples(index=False)]

    return list_sessions
