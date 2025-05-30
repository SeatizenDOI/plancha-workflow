import csv
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from argparse import Namespace

from .enum.FolderType import FolderType, get_foldertype_from_value, get_full_folder

class ConfigManager:

    def __init__(self, opt: Namespace) -> None:

        self.opt = opt
        self.cfg_prog = None
        self.default_args = {}
        self.list_sessions = []
        self.delta_time = None
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

        # Frame per second.
        self.default_args["frames_per_second"] = self.cfg_prog['dcim']['frames_per_second']


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

        # GPS values based on arguments.
        if rgp_station != "":
            self.cfg_prog['gps']['force_use_rgp'] = True
            self.cfg_prog['gps']['rgp_station'] = rgp_station
        else:
            self.cfg_prog['gps']['force_use_rgp'] = self.default_args["force_use_rgp"]
            self.cfg_prog['gps']['rgp_station'] = self.default_args["rgp_station"]
        
        self.cfg_prog['dcim']['frames_per_second'] = self.default_args["frames_per_second"]
        
        self.cfg_prog['mesh']['spacing_m'] = ""
        ### Add specific filtering interval values
        if filt_exclude_specific_timeUS != "":
            self.cfg_prog['gps']['filt_exclude_specific_timeUS'] = json.loads(filt_exclude_specific_timeUS)
        else:
            self.cfg_prog['gps']['filt_exclude_specific_timeUS'] = []
        ### Max/Min depth
        if depth_range_max != "":
            self.cfg_prog['bathy']['dpth_range']['max'] = float(depth_range_max)
        else:
            self.cfg_prog['bathy']['dpth_range']['max'] = self.default_args["max_depth"]
        
        if depth_range_min != "":
            self.cfg_prog['bathy']['dpth_range']['min'] = float(depth_range_min)
        else:
            self.cfg_prog['bathy']['dpth_range']['min'] = self.default_args["min_depth"]

        if filt_exclude_specific_datetimeUTC != "":
            self.cfg_prog['dcim']['filt_exclude_specific_datetimeUTC'] = filt_exclude_specific_datetimeUTC
        else:
            self.cfg_prog['dcim']['filt_exclude_specific_datetimeUTC'] = []
            
        self.delta_time = None


    def iterate_over_session(self):
        for args in self.list_sessions:
            
            self.update_cfg_prog_for_session(args)
            session_name, filt_exclude_specific_datetimeUTC = args[0], args[6]

            yield (session_name, filt_exclude_specific_datetimeUTC) 


    def save_cfg_prog(self, prog_config_path: Path) -> None:
        """ Save cfg prog file to provide path"""

        copy_prog = self.cfg_prog.copy()
        copy_prog["creation_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(prog_config_path, 'w') as fp:
            json.dump(copy_prog, fp,indent=3)
    

    # -- Getter part
    def get_root_path(self) -> str:
        return self.cfg_prog["session_info"]["root"]
    
    def get_session_name(self) -> str:
        return self.cfg_prog["session_info"]["session_name"]
    
    def get_exiftool_metadata_path(self) -> Path:
        return Path(self.cfg_prog["dcim"]["exiftool_config_path"])

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

    def get_leap_second(self) -> int:
         # for the leap second definition please refer to : https://fr.wikipedia.org/wiki/Synchronisation_GPS
         return int(self.cfg_prog['dcim']['leap_sec'])

    def get_frames_per_second(self) -> str:
        return self.cfg_prog["dcim"]["frames_per_second"]
    
    def get_time_first_frame(self) -> str:
        # N.B. insert the date and time following the format "YYYY:MM:DD HH:MM:SS.000"
        # N.B. insert the time in UTC+0 format
        # correct time by adding leap seconds to match GPS time (in 2023 it is 18 s)
            
        time_first_frame = self.cfg_prog['dcim']['time_first_frame_UTC']
        d_date = datetime.strptime(time_first_frame , '%Y:%m:%d %H:%M:%S.%f')
        d_date += pd.Timedelta(seconds = self.get_leap_second())
        time_first_frame = d_date.strftime('%Y:%m:%d %H:%M:%S.%f')

        return time_first_frame
    
    def get_first_frame_to_keep(self) -> int:
        return int(self.cfg_prog["dcim"]["first_frame_to_keep"])
    
    def get_rgp_station(self) -> str:
        return self.cfg_prog['gps']['rgp_station']
    
    def get_delta_time(self) -> str:

        if self.delta_time == None:
            fps = self.get_frames_per_second()
            a, b = [float(i) for i in fps.split('/')] if "/" in fps else (float(fps), 1)
            self.delta_time = str(1/(a/b))

        return self.delta_time
    
    def get_ppk_config_path(self) -> Path:
        ppk_config_file = Path(self.cfg_prog['gps']['ppk_config_path'], f"{self.cfg_prog['gps']['ppk_config_name']}.conf")

        if not ppk_config_file.exists():
            raise NameError("Cannot found ppk_config_file.")
        return ppk_config_file
    
    def get_parse_keys(self) -> dict:
        return self.cfg_prog["parse"]

    def get_parse_key_gps(self) -> dict:
        return self.cfg_prog["parse"]["gpskey"]
    
    def get_parse_key_att(self) -> str:
        return self.cfg_prog["parse"]["attkey"]
    
    def get_parse_key_depth(self) -> str:
        return self.cfg_prog["parse"]["dpthkey"]

    def get_filt_exclude_specific_timeUS(self) -> list:
        return self.cfg_prog["gps"]["filt_exclude_specific_timeUS"]
    
    def get_utm_zone(self) -> str:
        return self.cfg_prog["gps"]["utm_zone"]

    def get_utm_south(self) -> bool:
        return self.cfg_prog["gps"]["utm_south"]
    
    def get_utm_ellips(self) -> str:
        return self.cfg_prog["gps"]["utm_ellips"]
    
    def get_bathy_max_angle(self) -> int:
        return int(self.cfg_prog['bathy']['max_angle'])
    
    def get_bathy_depth_min(self) -> float:
        return float(self.cfg_prog['bathy']['dpth_range']['min'])

    def get_bathy_depth_max(self) -> float:
        return float(self.cfg_prog['bathy']['dpth_range']['max'])
    
    def get_bathy_dpth_win_s(self) -> float:
        return float(self.cfg_prog['bathy']['dpth_win_s'])
    
    def get_bathy_dpth_valid_prop(self) -> float:
        return float(self.cfg_prog['bathy']['dpth_valid_prop'])

    def get_geoid_path(self) -> Path:
        return Path(self.cfg_prog["bathy"]['geoid_path'])
    
    def get_off_ant_beam_x(self) -> float:
        return float(self.cfg_prog["bathy"]['offset_ant_beam']['x'])

    def get_off_ant_beam_y(self) -> float:
        return float(self.cfg_prog["bathy"]['offset_ant_beam']['y'])
    
    def get_off_ant_beam_z(self) -> float:
        return float(self.cfg_prog["bathy"]['offset_ant_beam']['z'])

    def get_dpth_coeff(self) -> float:
        return float(self.cfg_prog["bathy"]['dpth_coeff'])

    def get_mesh_spacing_m(self) -> float:
        return float(self.cfg_prog['mesh']['spacing_m'])

    def get_mesh_method(self) -> str:
        return self.cfg_prog['mesh']['method']

    def get_mesh_3dalgo(self) -> str:
        return self.cfg_prog['mesh']['3Dalgo']

    # -- Setter part

    def set_frames_per_second(self, frames_per_second: str) -> None:
        self.cfg_prog["dcim"]["frames_per_second"] = frames_per_second
    
    def set_mesh_spacing_m(self, spacing: float) -> None:
        self.cfg_prog['mesh']['spacing_m'] = spacing
    
    def set_force_rgp(self, v: bool) -> None:
        self.cfg_prog['gps']['force_use_rgp'] = v
    
    def set_filt_exclude_specific_datetimeUTC(self, filt_exclude_specific_datetimeUTC: list) -> None:
        self.cfg_prog['dcim']['filt_exclude_specific_datetimeUTC'] = filt_exclude_specific_datetimeUTC
    
    # -- Boolean method

    def can_split(self) -> bool:
        return not bool(self.opt.no_split)

    def is_only_split(self) -> bool:
        return bool(self.opt.only_split)
    
    def is_rtkfix(self) -> bool:
        return bool(self.cfg_prog["gps"]["filt_rtkfix"])
    
    def force_rgp(self) -> bool:
        return bool(self.cfg_prog['gps']['force_use_rgp'])
    
    def use_llh_position(self) -> bool:
        return bool(self.cfg_prog["gps"]["use_llh_position"])

    def gpsbaseposition_mean_on_llh(self) -> bool:
        return bool(self.cfg_prog["gps"]["gpsbaseposition_mean_on_llh"])

    def compute_bathy(self) -> bool:
        return not bool(self.opt.no_bathy)

    def dont_tags_frames(self) -> bool:
        return bool(self.opt.no_tags)
    
    def filter_on_waypoints(self) -> bool:
        return bool(self.cfg_prog["gps"]["filt_waypoint"])
    
    def use_geoid(self) -> bool:
        return bool(self.cfg_prog["bathy"]["use_geoid"])
    
    def should_I_remove_frames_outside_mission(self) -> bool:
        return bool(self.cfg_prog["dcim"]["remove_frames_outside_mission"])