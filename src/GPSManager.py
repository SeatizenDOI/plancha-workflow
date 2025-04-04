
import math
import wget
import shutil
import zipfile
import hatanaka
import pandas as pd
from pathlib import Path
from datetime import datetime
from subprocess import Popen, PIPE, CalledProcessError

from .ConfigManager import ConfigManager

from .enum.StandardDeviationType import StandardDeviationType

from .lib.lib_tools import llh_to_txt, get_hours_from_bin_sensors, replace_line, pos_to_llh
from .lib.lib_plot import plot_gps_quality, plot_standard_deviation

class GPSManager:

    def __init__(self, device_path: Path, base_path: Path) -> None:
        
        self.device_path = device_path
        self.base_path = base_path

        self.device_LLH_filepath = None
        self.device_RINEX_filepath = None
        self.base_LLH_filepath = None
        self.base_RINEX_filepath = None
        self.base_RGP_filepath = None

        self.ppk_solution = None # LLH file to store data.


    def setup(self, cm: ConfigManager, session_filepath: Path) -> None:
        """ Search and extract LLH file and RINEX"""

        print("\n-- Extract GPS data from zip files\n")
    
        # Extract all zip file in base and device.
        for file in [*list(self.device_path.iterdir()), *list(self.base_path.iterdir())]:
            if file.suffix.lower() != ".zip": continue
            
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(Path(file.parent, file.stem))
        
        self.device_LLH_filepath, self.device_RINEX_filepath = self.walk_in_zip_folder(self.device_path)
        self.base_LLH_filepath, self.base_RINEX_filepath = self.walk_in_zip_folder(self.base_path)


        print(f"Device LLH Path: {self.device_LLH_filepath.name if self.device_LLH_filepath != None else 'Not found'}")
        print(f"Device Rinex Path: {self.device_RINEX_filepath.name if self.device_RINEX_filepath != None else 'Not found'}")
        print(f"Base LLH Path: {self.base_LLH_filepath.name if self.base_LLH_filepath != None else 'Not found'}")
        print(f"Base Rinex Path: {self.base_RINEX_filepath.name if self.base_RINEX_filepath != None else 'Not found'}")

        # If we have an LLH folder, then plot a quality study on the GPS data before doing ppk.
        if self.device_LLH_filepath != None and self.device_LLH_filepath.exists():
            self.GPS_position_accuracy(session_filepath, self.device_LLH_filepath, cm.is_rtkfix())
        else:
            print("[WARNING] No LLH found. Cannot create preliminary plot.")


    def need_compute_gps(self) -> bool:
        # Before to extract all file, we try to see if we have already compute ppk solution.
        for file in self.device_path.iterdir():
            if "ppk_solution" in file.name and file.suffix == ".LLH":
                print("We already have a GPS file with PPK solution")
                self.ppk_solution = file
                return False
        return True


    def walk_in_zip_folder(self, path_to_walk: Path) -> tuple[Path | None, Path | None]:
        """ Walk inside a folder and search LLH File and Rinex folder. Return path if found else None """

        llh_path, rinex_path = None, None
        for file in path_to_walk.iterdir():
            if file.suffix == ".zip": continue
            
            if "LLH" in file.name and file.is_dir():
                llh_path = Path(file, f"{file.name.replace("_LLH", "")}.LLH")
            elif "RINEX" in file.name and file.is_dir():
                rinex_path = file
            elif file.is_dir(): # Sometimes, like RS3, the compression format is different.
                for subfile in file.iterdir():
                    if subfile.suffix == ".LLH":
                        llh_path = subfile
                    elif "RINEX" in subfile.name and subfile.is_dir():
                        rinex_path = subfile
        
        return llh_path, rinex_path

    def can_perform_ppk(self) -> bool:
        return self.device_RINEX_filepath != None and (self.base_RINEX_filepath != None or self.base_RGP_filepath != None)


    def GPS_position_accuracy(self, session_info_path: Path, llh_path: Path, flag_rtkfix: bool) -> None:
        """ Compute Q1, Q2 and Q5 to plot some graph. """

        # Inputs :
        # 1.llh_path = path of the llh file 
        llh_text_path  = llh_to_txt(llh_path)
        csv_llh = pd.read_csv(llh_text_path)
        
        session_info = pd.read_csv(session_info_path)
        # compute quality indexes and write in the session_info df
        session_info["Q1 ppk Percentage"] = len(csv_llh[csv_llh['fix']==1])/len(csv_llh) if len(csv_llh[csv_llh['fix']==1]) != 0 else 0
        session_info["Q2 ppk Percentage"] = len(csv_llh[csv_llh['fix']==2])/len(csv_llh) if len(csv_llh[csv_llh['fix']==2]) != 0 else 0
        session_info["Q5 ppk Percentage"] = len(csv_llh[csv_llh['fix']==5])/len(csv_llh) if len(csv_llh[csv_llh['fix']==5]) != 0 else 0
        # remove empy and Nan columns
        nan_value = float("NaN")
        session_info.replace("", nan_value, inplace=True)
        session_info.dropna(how='all', axis=1, inplace=True)
        # save session_info df
        session_info.to_csv(session_info_path, sep = ',', index=False)

        isPPK = "ppk" in llh_text_path.name

        # 1.PLOT GPS QUALITY
        plot_gps_quality(self.device_path, csv_llh, session_info, 'GPS_ppk_position_accuracy.png' if isPPK else 'GPS_position_accuracy.png')

        # 2. plot standard deviation north distribution before the filter
        plot_standard_deviation(self.device_path, csv_llh, f"sdn{'_ppk' if isPPK else ''}.png", StandardDeviationType.NORTH)

        # 3. plot standard deviation east distribution before the filter
        plot_standard_deviation(self.device_path, csv_llh, f"sde{'_ppk' if isPPK else ''}.png", StandardDeviationType.EAST)

        # if we are filtering on fix=1 then make another plot, but only if we have a ppk file
        if isPPK and flag_rtkfix :

            # 4. plot standard deviation distribution before the filter
            # filter on fix data
            csv_llh_fix = csv_llh[csv_llh['fix'] == 1]
            percentage_keep = len(csv_llh_fix) / len(csv_llh) if len(csv_llh) != 0 else 0
            print("If we filter on fix=1 e keep ", percentage_keep, " of the values")
            plot_standard_deviation(self.device_path, csv_llh, 'sdn_fix=1_ppk.png', StandardDeviationType.NORTH)
            plot_standard_deviation(self.device_path, csv_llh, 'sde_fix=1_ppk.png', StandardDeviationType.EAST)
    

    def download_rgp(self, cm: ConfigManager, session_name: str, frames_path: Path, sensors_path: Path) :

        alphabet = "abcdefghijklmnopqrstuvwx"

        # Get the session date from the session name
        session_date = session_name[0:8]
        # Convert to date object
        session_date2 = datetime.strptime(session_date, "%Y%m%d")

        # Day of the year
        doy = str(session_date2.timetuple().tm_yday).zfill(3)

        # Year
        y = session_date[0:4]

        # Last two digits of the year
        yy = y[2:4]

        # Hour
        nb_frames = len(list(frames_path.iterdir()))
        hour_start = int(cm.get_time_first_frame()[11:13])
        hour_end = hour_start + math.ceil(nb_frames*float(cm.get_delta_time())/3600)

        # If no frames, get hours from sensor file
        if nb_frames == 0:
            hour_start, hour_end = get_hours_from_bin_sensors(session_name, sensors_path)
        
        rgp_station = cm.get_rgp_station()
        
        # Download
        for h in range(hour_start, hour_end+1):
            url = f"ftp://rgpdata.ign.fr/pub/data/{y}/{doy}/data_1/{rgp_station}{doy}{alphabet[h]}.{yy}d.Z"
            print(f"\nRetrieve from {url}")
            wget.download(url, out=str(self.base_path))

        # Uncompress downloaded files
        for file in self.base_path.iterdir() :
            if file.suffix == ".Z":
                print(f"\nUncompress {file}")
                hatanaka.decompress_on_disk(str(file))

        # Merged rinex file
        isFirst = False
        self.base_RGP_filepath = Path(self.base_path,f"{rgp_station}{doy}_merged.o")
        with open(self.base_RGP_filepath, "w") as merged_rinex:
            for file in sorted(list(self.base_path.iterdir())) :
                if file.suffix != f".{yy}o": continue

                with open(file, "r") as file_rinex:
                    if isFirst == False:
                        merged_rinex.write(file_rinex.read())
                        isFirst = True
                    else:
                        a = file_rinex.readline()
                        while "END OF HEADER" not in a:
                            a = file_rinex.readline()
                        merged_rinex.write(file_rinex.read())
        
    def ppk(self, cm: ConfigManager, session_name: str) -> None:

        ppk_config_file = cm.get_ppk_config_path()
        dest_ppk_config_file = Path(self.device_path, f"{ppk_config_file.stem}_{session_name}{ppk_config_file.suffix}")
        shutil.copy(ppk_config_file, dest_ppk_config_file)

        baseFile = None

        if self.base_RGP_filepath != None:
            # Change ppk_config to be ready for rgp station
            replace_line(dest_ppk_config_file, 3, 'pos1-frequency     =2   # (1:l1,2:l1+l2,3:l1+l2+l5,4:l1+l5)\n')
            replace_line(dest_ppk_config_file, 5, 'pos1-elmask       =30         # (deg)\n')
            replace_line(dest_ppk_config_file, 96, 'ant1-postype       =rinexhead        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
            replace_line(dest_ppk_config_file, 104, 'ant2-postype       =rinexhead        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
            replace_line(dest_ppk_config_file, 105, 'ant2-pos1          =0  # (deg|m)\n')
            replace_line(dest_ppk_config_file, 106, 'ant2-pos2          =0  # (deg|m)\n')
            replace_line(dest_ppk_config_file, 107, 'ant2-pos3          =0  # (m|m)\n')
            baseFile = str(self.base_RGP_filepath)
        
        elif self.base_RINEX_filepath != None:
            for file in self.base_RINEX_filepath.iterdir():
                if "o" in file.suffix.lower() or "obs" in file.suffix.lower():
                    baseFile = str(file)

            if cm.gpsbaseposition_mean_on_llh() and self.base_LLH_filepath.exists():
                print("Perform GPSBase mean on LLH")
                # read the Base LLH file in order to compute mean of x, y, z
                baseLLH_csv = pd.read_csv(llh_to_txt(self.base_LLH_filepath))
                status_fix = 1 if len(baseLLH_csv[baseLLH_csv['fix']==1]) > 0 else (2 if len(baseLLH_csv[baseLLH_csv['fix']==2]) > 0 else 5)
                # replace ppk config position only if the config file is not the aldabra one
                replace_line(dest_ppk_config_file, 96, 'ant1-postype       =llh        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
                replace_line(dest_ppk_config_file, 104, 'ant2-postype       =llh        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
                # compute base position by calculating the mean of the base LLH file, only when stauts_fix==1
                replace_line(dest_ppk_config_file, 105, 'ant2-pos1          =%4.14f  # (deg|m)\n' %baseLLH_csv[baseLLH_csv['fix']==status_fix]["GPSLatitude"].mean())
                replace_line(dest_ppk_config_file, 106, 'ant2-pos2          =%4.14f  # (deg|m)\n' %baseLLH_csv[baseLLH_csv['fix']==status_fix]["GPSLongitude"].mean())
                replace_line(dest_ppk_config_file, 107, 'ant2-pos3          =%4.14f  # (m|m)\n' %baseLLH_csv[baseLLH_csv['fix']==status_fix]["elevation"].mean())


        else:
            raise NameError("RGP filepath and Base Rinex filepath are None. Cannot perform PPK.")

        if baseFile == None:
            raise NameError("Cannot perform ppk. Rinex files or RGP files for base where not found.")

        ## Device.
        deviceFile, navFile = None, None
        for file in self.device_RINEX_filepath.iterdir():
            if "o" in file.suffix.lower() or "obs" in file.suffix.lower():
                deviceFile = str(file)

            if "p" in file.suffix.lower() or "nav" in file.suffix.lower():
                navFile = str(file)
        
        if navFile == None or deviceFile == None:
            raise NameError("Cannot perform ppk. Rinex files for device where not found.")
        
        ## Perform PPK with rtklib.
        print("We are currently doing PPK on session : ", session_name)
        pos_path = Path(self.device_path, f"ppk_solution_{session_name}.pos")
        # Create command to run solution
        # -x : debug trace level (0:off)
        # -y : output solution status (0:off,1:states,2:residuals)
        # -k : config options
        # -o : output file
        # Q = 1:fix, 2:float, 3:sbas, 4:dgps, 5:single, 6:ppp
        with Popen(["rnx2rtkp", "-x", "0", "-y", "2", "-k", dest_ppk_config_file,"-o", str(pos_path), deviceFile, baseFile, navFile], stdout=PIPE, bufsize=1, universal_newlines=True) as p:
            for line in p.stdout:
                print(line, end='')

            p.wait() # Wait because sometimes Python is too fast.
            if p.returncode != 0:
                raise CalledProcessError(p.returncode, p.args)

        self.ppk_solution = pos_to_llh(pos_path)
    

    def get_navigation_file_in_text(self) -> Path:
        return llh_to_txt(self.ppk_solution)