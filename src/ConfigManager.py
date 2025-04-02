import csv
import json
from pathlib import Path
from argparse import Namespace

from .enum.FolderType import FolderType, get_foldertype_from_value, get_full_folder

class ConfigManager:

    def __init__(self, opt: Namespace):

        self.opt = opt
        self.cfg_prog = None
        self.default_args = {}
        self.list_sessions = []
        self.setup()

    def setup(self) -> None:

        self.load_cfg_prog_file()
        self.parse_and_get_default_args()

        self.build_sessions_to_process()


    def load_cfg_prog_file(self) -> None:
        """ Check and load cfg prog file. """
        # Open json file with config of the session
        if self.opt.plancha_config_path != None:
            default_plancha_config = Path(self.opt.plancha_config_path)
        else:
            print("[WARNING] Plancha config file not provide. Default file was used plancha_config/plancha_config.json")
            default_plancha_config = Path("./plancha_config/plancha_config.json")


        if not default_plancha_config.exists():
            raise NameError(f"Plancha config path was not found for {default_plancha_config}")

        with open(default_plancha_config) as json_file:
            self.cfg_prog = json.load(json_file)
        
    
    def parse_and_get_default_args(self) -> None:

        # Override root path
        if self.opt.root_path:
            self.cfg_prog["session_info"]["root"] = self.opt.root_path
        
        # Saved default max depth
        self.default_args["max_depth"] = float(self.cfg_prog['bathy']['dpth_range']['max'])
        self.default_args["min_depth"] = float(self.cfg_prog['bathy']['dpth_range']['min'])
        
        # La Reunion only
        # flag for force rgp station
        self.default_args["force_use_rgp"] = True if self.cfg_prog['gps']['force_use_rgp'] else self.opt.force_use_rgp
        self.default_args["rgp_station"] = str(self.cfg_prog['gps']['rgp_station'])

    def build_sessions_to_process(self) -> None:

        # Build a list of [SESSION_NAME, FIRST_FRAME_UTC, FIRST_FRAME_NUMBER, filt_exclude_specific_timeUS, depth_range_max, depth_range_min, filt_exclude_specific_datetimeUTC, default_rgp_station]
        self.list_sessions = [[
            self.cfg_prog['session_info']['session_name'], 
            str(self.cfg_prog['dcim']['time_first_frame_UTC']), 
            int(self.cfg_prog['dcim']['first_frame_to_keep']), 
            str(self.cfg_prog['gps']['filt_exclude_specific_timeUS']), 
            self.default_args["max_depth"],
            self.default_args["min_depth"],
            str(self.cfg_prog['dcim']['filt_exclude_specific_datetimeUTC']),
            "" # Don't fill with rgp station name to avoid force use by mistake
        ]]

        # If we have a csv file we parse it, else we return
        if self.opt.csv == None or not Path(self.opt.csv).exists(): return
        
        DEFAULT_SIZE = len(self.list_sessions[0])
        self.list_sessions = [] # Remove all list content.
        with open(self.opt.csv, "r") as csvfile:
            spamreader = csv.reader(csvfile, delimiter=',')
            header = next(spamreader, None) # Skip header row.

            for row in spamreader:
                if len(row) == DEFAULT_SIZE:
                    self.list_sessions.append(row)
                else:
                    self.list_sessions.append(row + [""] * (DEFAULT_SIZE - len(row))) # When we don't have all column fill or existing.
  

    def update_cfg_prog_for_session(self, args: list) -> None:

        session_name, time_first_frame, number_first_frame, \
        filt_exclude_specific_timeUS, depth_range_max, depth_range_min, \
        filt_exclude_specific_datetimeUTC, rgp_station = args

        self.cfg_prog['session_info']['session_name'] = session_name
        self.cfg_prog['dcim']['time_first_frame_UTC'] = time_first_frame
        self.cfg_prog['dcim']['first_frame_to_keep'] = int(self.opt.remove_frames) if self.opt.remove_frames and self.opt.remove_frames.isnumeric() else number_first_frame # Override

        if rgp_station != "":
            self.cfg_prog['gps']['force_use_rgp'] = True
            self.cfg_prog['gps']['rgp_station'] = rgp_station
        else:
            self.cfg_prog['gps']['force_use_rgp'] = self.default_args["force_use_rgp"]
            self.cfg_prog['gps']['rgp_station'] = self.default_args["rgp_station"]



    def iterate_over_session(self):
        for args in self.list_sessions:
            
            self.update_cfg_prog_for_session(args)


            yield args 


    def save_cfg_prog(self, prog_congig_path: Path) -> None:
        """ Save cfg prog file to provide path"""

        print("\n-- Finally, save plancha_config.json\n")
        with open(prog_congig_path, 'w') as fp:
            json.dump(self.cfg_prog, fp,indent=3)
    

    # -- Getter part
    def get_root_path(self) -> str:
        return self.cfg_prog["session_info"]["root"]
    
    def get_folder_to_clean(self) -> list[FolderType]:
        
        # If no clean, return.
        if not self.cfg_prog["session_info"]["delete_processed_session"]: return []

        # Get all folders to clean.
        folders_to_clean = get_full_folder()
        
        # Don't clean folder specify by no_clean arg.
        for char in self.opt.no_clean:
            folder_to_not_clean = get_foldertype_from_value(char)
            folders_to_clean.remove(folder_to_not_clean)
        
        return folders_to_clean