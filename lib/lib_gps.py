import os
import wget
import math
import shutil
import zipfile
import hatanaka
import pandas as pd
from pathlib import Path
from datetime import datetime
from subprocess import Popen, PIPE, CalledProcessError

from lib.lib_plot import *
from lib.lib_tools import llh_to_txt, pos_to_llh, replace_line, get_hours_from_bin_sensors, gpx_to_llh

def GPS_position_accuracy(SESSION_INFO_PATH, LLH_PATH, GPS_DEVICE_PATH, flag_rtkfix) :
    # Inputs :
    # 1.llh_path = path of the llh file 
    TXT_PATH  = llh_to_txt(LLH_PATH)
    csv_llh = pd.read_csv(TXT_PATH)
    
    session_info = pd.read_csv(SESSION_INFO_PATH)
    # compute quality indexes and write in the session_info df
    session_info["Q1 ppk Percentage"] = len(csv_llh[csv_llh['fix']==1])/len(csv_llh) if len(csv_llh[csv_llh['fix']==1]) != 0 else 0
    session_info["Q2 ppk Percentage"] = len(csv_llh[csv_llh['fix']==2])/len(csv_llh) if len(csv_llh[csv_llh['fix']==2]) != 0 else 0
    session_info["Q5 ppk Percentage"] = len(csv_llh[csv_llh['fix']==5])/len(csv_llh) if len(csv_llh[csv_llh['fix']==5]) != 0 else 0
    # remove empy and Nan columns
    nan_value = float("NaN")
    session_info.replace("", nan_value, inplace=True)
    session_info.dropna(how='all', axis=1, inplace=True)
    # save session_info df
    session_info.to_csv(SESSION_INFO_PATH, sep = ',', index=False)

    isPPK = "ppk" in TXT_PATH

    # 1.PLOT GPS QUALITY
    plot_gps_quality(GPS_DEVICE_PATH, csv_llh, session_info, 'GPS_ppk_position_accuracy.png' if isPPK else 'GPS_position_accuracy.png')

    # 2. plot standard deviation north distribution before the filter
    plot_standard_deviation_north(GPS_DEVICE_PATH, csv_llh, 'sdn_ppk.png' if isPPK else 'sdn.png')

    # 3. plot standard deviation east distribution before the filter
    plot_standard_deviation_east(GPS_DEVICE_PATH, csv_llh, 'sde_ppk.png' if isPPK else 'sde.png')

    # if we are filtering on fix=1 then make another plot, but only if we have a ppk file
    if isPPK and flag_rtkfix :

        # 4. plot standard deviation distribution before the filter
        # filter on fix data
        csv_llh_fix = csv_llh[csv_llh['fix'] == 1]
        percentage_keep = len(csv_llh_fix) / len(csv_llh) if len(csv_llh) != 0 else 0
        print("If we filter on fix=1 e keep ", percentage_keep, " of the values")
        plot_standard_deviation_north(GPS_DEVICE_PATH, csv_llh, 'sdn_fix=1_ppk.png')
        plot_standard_deviation_east(GPS_DEVICE_PATH, csv_llh, 'sde_fix=1_ppk.png')
      
    return TXT_PATH


def download_rgp(SESSION_NAME, time_first_frame, FRAMES_PATH, GPS_BASE_PATH, SENSOR_PATH, rgp_station, delta_time) :

    alphabet = "abcdefghijklmnopqrstuvwx"

    # Get the session date from the session name
    session_date = SESSION_NAME[0:8]
    # Convert to date object
    session_date2 = datetime.strptime(session_date, "%Y%m%d")

    # Day of the year
    doy = str(session_date2.timetuple().tm_yday).zfill(3)

    # Year
    y = session_date[0:4]

    # Last two digits of the year
    yy = y[2:4]

    # Hour
    nb_frames = len(os.listdir(FRAMES_PATH))
    hour_start = int(time_first_frame[11:13])
    hour_end = hour_start + math.ceil(nb_frames*float(delta_time)/3600)

    # If no frames, get hours from sensor file
    if nb_frames == 0:
        hour_start, hour_end = get_hours_from_bin_sensors(SESSION_NAME, SENSOR_PATH)

    # Download
    for h in range(hour_start, hour_end+1):
        url = f"ftp://rgpdata.ign.fr/pub/data/{y}/{doy}/data_1/{rgp_station}{doy}{alphabet[h]}.{yy}d.Z"
        print(f"\nRetrieve from {url}")
        wget.download(url, out=GPS_BASE_PATH)

    # Uncompress downloaded files
    GPS_BASE_PATH = Path(GPS_BASE_PATH)
    for file in GPS_BASE_PATH.iterdir() :
        if file.suffix == ".Z":
            print(f"\nUncompress {file}")
            hatanaka.decompress_on_disk(str(file))

    # Merged rinex file
    isFirst = False
    with open(Path(GPS_BASE_PATH,f"{rgp_station}{doy}_merged.o"), "w") as merged_rinex:
        for file in sorted(list(GPS_BASE_PATH.iterdir())) :
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
    flag_base = 2
    return flag_base

def ppk(SESSION_NAME, GPS_BASE_PATH, GPS_DEVICE_PATH, PPK_CONFIG_PATH, ppk_cfgs, flag_base, gpsbaseposition_mean_on_llh) :

    date_reach = SESSION_NAME[0:8]

    #######################################################################
    ########################### BASE ######################################
    #######################################################################

    # work on a copy of the config file so that if we modify it, we keep original file clean 
    ppk_config_file = PPK_CONFIG_PATH + ppk_cfgs[0] + ".conf"
    file_name = ppk_cfgs[0] + "_" + SESSION_NAME + ".conf"
    ppk_config_dest_file = GPS_DEVICE_PATH + "/" + file_name
    shutil.copy(ppk_config_file, ppk_config_dest_file)

    # If we have RINEX data
    if (flag_base == 1) :
    
        for folder in os.listdir(GPS_BASE_PATH) : 
            # Look for the RINEX folder
            if ("RINEX" in folder) :
                # Check that the session date is the same as the base gps file date
                if (date_reach in folder) :

                    baseRINEX = GPS_BASE_PATH + "/" + folder.replace(".zip", "") + "/"

                    # If it is a zipped folder, unzip it
                    if folder.endswith(".zip") :
                        
                        with zipfile.ZipFile(GPS_BASE_PATH + "/" + folder, 'r') as zip_ref:
                            zip_ref.extractall(baseRINEX)
                else :
                    print('WARNING : The date of base file "', folder, '" does not match the session date')
                break
        
        for file in os.listdir(baseRINEX) : 
            if file.endswith("O") or file.endswith(".obs") :
                baseFile = baseRINEX + file
        


        # Run a solution for each config file in list 
        # if we have a gps base than write the mean of the LLH file in the ppk config file (if gpsbaseposition_mean_on_llh = true)
        if gpsbaseposition_mean_on_llh :
            for folder in os.listdir(GPS_BASE_PATH) : 
                # Look for the RINEX folder
                if ("LLH" in folder) :
                    # Check that the session date is the same as the base gps file date
                    if (date_reach in folder) :
                        baseLLH = GPS_BASE_PATH + "/" + folder.replace(".zip", "") + "/"

                        # If it is a zipped folder, unzip it
                        if folder.endswith(".zip") :
                            with zipfile.ZipFile(GPS_BASE_PATH + "/" + folder, 'r') as zip_ref:
                                zip_ref.extractall(baseLLH)

                        for file in os.listdir(baseLLH) : 
                            if file.endswith("LLH") :
                                baseLLHfile_path = baseLLH + file
                        # read the Base LLH file in order to compute mean of x, y, z
                        baseLLH_csv = pd.read_csv(llh_to_txt(baseLLHfile_path))
                        status_fix = 1 if len(baseLLH_csv[baseLLH_csv['fix']==1]) > 0 else (2 if len(baseLLH_csv[baseLLH_csv['fix']==2]) > 0 else 5)
                        # replace ppk config position only if the config file is not the aldabra one
                        replace_line(ppk_config_dest_file, 96, 'ant1-postype       =llh        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
                        replace_line(ppk_config_dest_file, 104, 'ant2-postype       =llh        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
                        # compute base position by calculating the mean of the base LLH file, only when stauts_fix==1
                        replace_line(ppk_config_dest_file, 105, 'ant2-pos1          =%4.14f  # (deg|m)\n' %baseLLH_csv[baseLLH_csv['fix']==status_fix]["GPSLatitude"].mean())
                        replace_line(ppk_config_dest_file, 106, 'ant2-pos2          =%4.14f  # (deg|m)\n' %baseLLH_csv[baseLLH_csv['fix']==status_fix]["GPSLongitude"].mean())
                        replace_line(ppk_config_dest_file, 107, 'ant2-pos3          =%4.14f  # (m|m)\n' %baseLLH_csv[baseLLH_csv['fix']==status_fix]["elevation"].mean())

    # If we have RGP data
    if (flag_base == 2) :

        # Change ppk_config to be ready for rgp station
        replace_line(ppk_config_dest_file, 3, 'pos1-frequency     =2   # (1:l1,2:l1+l2,3:l1+l2+l5,4:l1+l5)\n')
        replace_line(ppk_config_dest_file, 5, 'pos1-elmask       =30         # (deg)\n')
        replace_line(ppk_config_dest_file, 96, 'ant1-postype       =rinexhead        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
        replace_line(ppk_config_dest_file, 104, 'ant2-postype       =rinexhead        # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm,6:raw)\n')
        replace_line(ppk_config_dest_file, 105, 'ant2-pos1          =0  # (deg|m)\n')
        replace_line(ppk_config_dest_file, 106, 'ant2-pos2          =0  # (deg|m)\n')
        replace_line(ppk_config_dest_file, 107, 'ant2-pos3          =0  # (m|m)\n')

        for file in os.listdir(GPS_BASE_PATH) : 
            # Get the merged observation file
            if file.endswith("merged.o") :
                baseFile = GPS_BASE_PATH + "/" + file


    #########################################################################
    ########################### DEVICE ######################################
    #########################################################################
    for folder in os.listdir(GPS_DEVICE_PATH) :

        # Look for the RINEX folder
        if ("RINEX" in folder) :
        
            deviceRINEX = GPS_DEVICE_PATH + "/" + folder.replace(".zip", "") + "/"

            # If it is a zipped folder, unzip it
            if folder.endswith(".zip") :
                
                with zipfile.ZipFile(GPS_DEVICE_PATH + "/" + folder, 'r') as zip_ref:
                    zip_ref.extractall(deviceRINEX)
            break

    # Get the obs and nav files
    for file in os.listdir(deviceRINEX) :

        if file.endswith("O") or file.endswith("obs") :
            deviceFile = deviceRINEX + file

        elif file.endswith("P") or file.endswith("nav") :
            navFile = deviceRINEX + file


    print("We are currently doing PPK on session : ", SESSION_NAME)
    pos_path = GPS_DEVICE_PATH + "/ppk_solution_" + SESSION_NAME + ".pos"
    # Create command to run solution
    # -x : debug trace level (0:off)
    # -y : output solution status (0:off,1:states,2:residuals)
    # -k : config options
    # -o : output file
    # Q = 1:fix, 2:float, 3:sbas, 4:dgps, 5:single, 6:ppp
    with Popen(["rnx2rtkp", "-x", "0", "-y", "2", "-k", ppk_config_dest_file,"-o", pos_path, deviceFile, baseFile, navFile], stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            print(line, end='')

        p.wait() # Wait because sometimes Python is too fast.
        if p.returncode != 0:
            raise CalledProcessError(p.returncode, p.args)

    llh_path = pos_to_llh(pos_path)
    return llh_path

def compute_gps(SESSION_INFO_PATH, GPS_DEVICE_PATH, GPS_BASE_PATH, SESSION_NAME, time_first_frame, FRAMES_PATH, SENSOR_PATH, rgp_station, delta_time, PPK_CONFIG_PATH, ppk_cfgs, flag_rtkfix, gpsbaseposition_mean_on_llh, cfg_prog):
    flag_gps = 0
    flag_device = 0   # old name = flag_gps
    flag_base = 0   # 1 : RINEX ; 2 : RGP
    TEMP_LLH_FOLDER_PATH = ""
    print("\n--2/6 Find best GPS position\n")
    ########################################################################################
    # Preliminary plot #
    ########################################################################################
    # if we have an LLH folder, then plot a quality study on the GPS data before doing ppk
    if os.path.isdir(GPS_DEVICE_PATH) :
        for folder in os.listdir(GPS_DEVICE_PATH) :
            if ("LLH" in folder) :
                TEMP_LLH_FOLDER_PATH = GPS_DEVICE_PATH + "/" + folder.replace(".zip", "") + "/"
                # If it is a zipped folder, unzip it
                if folder.endswith(".zip") :
                    with zipfile.ZipFile(GPS_DEVICE_PATH + "/" + folder, 'r') as zip_ref:
                        zip_ref.extractall(TEMP_LLH_FOLDER_PATH)
                    break
        if TEMP_LLH_FOLDER_PATH == "":
            raise NameError("/!\\ GPS DEVICE DOESN'T HAVE LLH /!\\")
        # Get the gps file
        for file in os.listdir(TEMP_LLH_FOLDER_PATH):
            if file.endswith(".LLH"):
                TEMP_LLH_PATH = TEMP_LLH_FOLDER_PATH + "/" + file
                GPS_position_accuracy(SESSION_INFO_PATH, TEMP_LLH_PATH, GPS_DEVICE_PATH, flag_rtkfix)
                break
    ########################################################################################

    # 0
    # ----- Check if we need to process PPK solution 
    if os.path.isdir(GPS_DEVICE_PATH) :
        for file in os.listdir(GPS_DEVICE_PATH) :
            if ("ppk_solution" in file) and (file.endswith(".LLH")):
                print("We already have a GPS file with PPK solution")
                LLH_PATH = GPS_DEVICE_PATH + "/" + file
                flag_gps = 1


    if (flag_gps == 0) :
    # ----- Check if we can process PPK solution 

        # 1- If we have a device RINEX folder
        if os.path.isdir(GPS_DEVICE_PATH) :
            for folder in os.listdir(GPS_DEVICE_PATH) :
                if ("RINEX" in folder) :
                    flag_device = 1


        # 2- If we have base GPS data
        if os.path.exists(GPS_BASE_PATH) :
            # 2.a - If we force to use RGP station, download data
            if cfg_prog["gps"]["force_use_rgp"] == True:
                print("Downloading RGP data from", rgp_station, "station :")
                flag_base = download_rgp(SESSION_NAME, time_first_frame, FRAMES_PATH, GPS_BASE_PATH, SENSOR_PATH, rgp_station, delta_time)

            # 2.b- If we have a base RINEX folder
            if (flag_base == 0):
                for folder in os.listdir(GPS_BASE_PATH) :
                    if ("RINEX" in folder) :
                        flag_base = 1

            # 2.c- If we don't have a RINEX folder, look for RGP files
            if (flag_base == 0) :
                for file in os.listdir(GPS_BASE_PATH) :
                    # 2.c.a- If we have data from RGP station
                    if file.endswith("d") :
                        flag_base = 2

            # 2.b.b- If we don't have data from RGP station, download it
            if (flag_base == 0) :
                print("Downloading RGP data from", rgp_station, "station :")
                flag_base = download_rgp(SESSION_NAME, time_first_frame, FRAMES_PATH, GPS_BASE_PATH, SENSOR_PATH, rgp_station, delta_time)
                cfg_prog["gps"]["force_use_rgp"] = True # Set to true to keep track

        if (flag_base != 0) and (flag_device != 0) :
            print("we can do PPK on our data !")
            LLH_PATH = ppk(SESSION_NAME, GPS_BASE_PATH, GPS_DEVICE_PATH, PPK_CONFIG_PATH, ppk_cfgs, flag_base, gpsbaseposition_mean_on_llh)
            flag_gps = 1


    # ----- If we cannot process PPK solution
    if (flag_gps == 0) :
        print("we cannot do PPK on our data at the moment !")
        
        # Look for the LLH folder
        if os.path.isdir(GPS_DEVICE_PATH) :
            for folder in os.listdir(GPS_DEVICE_PATH) :
                if ("LLH" in folder) :

                    LLH_FOLDER_PATH = GPS_DEVICE_PATH + "/" + folder.replace(".zip", "") + "/"
                    
                    # If it is a zipped folder, unzip it
                    if folder.endswith(".zip") :
                        
                        with zipfile.ZipFile(GPS_DEVICE_PATH + "/" + folder, 'r') as zip_ref:
                            zip_ref.extractall(LLH_FOLDER_PATH)
                        break
        
            # Get the gps file
            for file in os.listdir(LLH_FOLDER_PATH):
                if file.endswith(".LLH"):
                    flag_gps = 1
                    LLH_PATH = LLH_FOLDER_PATH + "/" + file
                    break

    # ----- Get the final GPS file with or without PPK solution
    # Check if we have a GPS file
    if flag_gps == 1 :
        TXT_PATH  = llh_to_txt(LLH_PATH)
        print("The NEW navigation file will be : ", TXT_PATH)
        return LLH_PATH, flag_gps
    else :
        print("We do not have a navigation file")
        return
    
def compute_gps_for_only_device(SESSION_INFO_PATH, GPS_DEVICE_PATH, flag_rtkfix):
    TXT_PATH = 'None'
    TEMP_LLH_FOLDER_PATH = ""
    if os.path.isdir(GPS_DEVICE_PATH) :
        for folder in os.listdir(GPS_DEVICE_PATH) :
            if ("LLH" in folder) :
                TEMP_LLH_FOLDER_PATH = GPS_DEVICE_PATH + "/" + folder.replace(".zip", "") + "/"
                # If it is a zipped folder, unzip it
                if folder.endswith(".zip") :
                    with zipfile.ZipFile(GPS_DEVICE_PATH + "/" + folder, 'r') as zip_ref:
                        zip_ref.extractall(TEMP_LLH_FOLDER_PATH)
                    break
            # If we have a gpx file, we convert it to llh file
            elif folder.endswith(".gpx"):
                TEMP_LLH_FOLDER_PATH = GPS_DEVICE_PATH
                gpx_to_llh(GPS_DEVICE_PATH + "/" +folder)

        if TEMP_LLH_FOLDER_PATH == "":
            raise NameError("/!\\ GPS DEVICE DOESN'T HAVE LLH /!\\")
        # Get the gps file
        for file in os.listdir(TEMP_LLH_FOLDER_PATH):
            if file.endswith(".LLH"):
                TEMP_LLH_PATH = TEMP_LLH_FOLDER_PATH + "/" + file
                TXT_PATH = GPS_position_accuracy(SESSION_INFO_PATH, TEMP_LLH_PATH, GPS_DEVICE_PATH, flag_rtkfix)
                break
    
    return TXT_PATH