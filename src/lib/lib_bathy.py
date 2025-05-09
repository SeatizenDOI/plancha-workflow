import csv
import time
import pyproj
import shutil
import subprocess
import numpy as np
import pandas as pd
from pathlib import Path
import transforms3d as t3d
from datetime import datetime
import matplotlib.pyplot as plt

from scipy.spatial import KDTree
from scipy.interpolate import interp1d, LinearNDInterpolator, griddata

from .lib_tools import convert_GMS_GWk_to_UTC_time

from ..ConfigManager import ConfigManager

def count_null_values_in_file(log_path: Path) -> int:
    with open(log_path, 'rb') as f:
        data = f.read()
        nullcnt = data.count( b'\x00' )
        print('... found', nullcnt, ' NULL bytes')
    return nullcnt


def clean_nullbyte_raw_log(log_path: Path) -> None:

    shutil.copy(log_path, Path(log_path.parent, f"{log_path.name}.bkp"))
    tmp_log_path = Path(log_path.parent, f"{log_path.name}.tmp")


    nullcnt = count_null_values_in_file(log_path)
    if not nullcnt: return
    
    with open(log_path, 'rb') as f:
        print('... parsing')
        data = f.readlines()
        
        with open(tmp_log_path, 'w') as of:
            print('... cleaning')
            for line in data:
                strline = line.decode("utf-8")[:-1]
                of.write(strline.replace('\x00', ''))
        
    nullcnt = count_null_values_in_file(tmp_log_path)
        
    shutil.move(tmp_log_path, log_path)


def parse_raw_log(log_path: Path, cfg_parse: dict) -> dict:
    # time func execution
    texec = datetime.now()
    
    print('Cleaning raw log ...')
    clean_nullbyte_raw_log(log_path)
    
    # Status list (fixed)
    # DEBUG !!! (MJULIEN --> Suppres MSG from parsed lines, causes bug on some log files)
    # status_list=['MODE','ARM']
    status_list=['MODE', 'ARM', 'MSG', 'CMD']
    
    # Read mandatory params from config dict
    param_list=[
        cfg_parse['gpskey'] , # mandatory
        cfg_parse['attkey'] , # mandatory
        cfg_parse['dpthkey'], # mandatory
    ]
    # Read optional params from config dict. Strip and split string in case of multiple params
    param_list.extend(cfg_parse['optkey'].strip().split(','))
    
    # init buffers
    datadict, headdict, dfdict = {}, {}, {}

    for param in [*param_list, *status_list]:
        datadict[param] = []
        headdict[param] = []
        dfdict[param]   = []
    
    #Parsing the log file
    print('func: parsing log for keys:')
    with open(log_path) as file:
        parsed=csv.reader(file,delimiter=',')
        for line in parsed:
            # check if it is an header line
            try:
                if line[0] == 'FMT':
                    # check if it is an header of interest
                    if line[3].strip() in param_list:
                        headdict[line[3].strip()].append([x.strip() for x in line[5:]])
                    if line[3].strip() in status_list:
                        headdict[line[3].strip()].append([x.strip() for x in line[5:]])
                # check if it is data line and if in param of interest
                if line[0] in param_list:
                    datadict[line[0]].append([float(x) for x in line[1:]])
                # check if it is status line and if in status of interest
                if line[0] in status_list:
                    datadict[line[0]].append([str(x) for x in line[1:]])
                    # statusdict[line[0]].append([str(x) for x in line[1:]])
            except:
                print('warning: Wrong formatting found, skipping line ...')
    # convert table to dataframe with correct column names
    for param in param_list:
        if param == '': continue
        dfdict[param] = pd.DataFrame(datadict[param],columns=headdict[param][0])
    for param in status_list:
        dfdict[param] = pd.DataFrame(datadict[param],columns=headdict[param][0])

    # time func execution
    print('func: exec time --> ',datetime.now() - texec)
    
    return dfdict

def parse_raw_bin(log_path: Path, cfg_parse: dict) -> dict:
    # time func execution
    texec = datetime.now()
    
    # Status list (fixed)
    status_list=['MODE', 'ARM', 'MSG', 'CMD']
    
    # Read mandatory params from config dict
    param_list = [
        cfg_parse['gpskey'] , # mandatory
        cfg_parse['attkey'] , # mandatory
        cfg_parse['dpthkey'], # mandatory
    ]

    # Read optional params from config dict. Strip and split string in case of multiple params
    opt = cfg_parse['optkey'].strip().split(',')
    if len(opt) > 0 and opt[0] != '':
        param_list.extend(opt)
    
    dfdict = {}
    
    #Parsing the bin file
    print('func: parsing log for keys:')
    print(param_list,status_list)
    
    for p in [*param_list, *status_list]:
        print('Reading data for entry:',p)

        filepath = Path("/tmp", f'tmp_{int(time.time())}.csv')
        filebuf = open(filepath, "w")
        
        tmp_cmd = ["python", "./src/lib/mavlogdump.py", "--planner", "--format", "csv", "--type", p, log_path]
        with subprocess.Popen(tmp_cmd, stdout=filebuf, universal_newlines=True) as popen:
            popen.wait() # Wait because sometimes Python is too fast.

        filebuf.close()

        dfdict[p] = pd.read_csv(filepath, sep=";")
        filepath.unlink()
        
        print('found',len(dfdict[p]),'points')
        
    # time func execution
    print('func: exec time --> ', datetime.now() - texec)

    return dfdict

def build_dataframe_gps(dfdict_dump_mavlog: dict, cm: ConfigManager, navigation_filepath: Path) -> tuple[pd.DataFrame, list]:
    # time func execution
    texec = datetime.now()
    
    df = dfdict_dump_mavlog[cm.get_parse_key_gps()].copy()
    print('func: initial dataframe has',len(df),'points')

    # use LLH position instead of the LOG/BIN one
    if cm.use_llh_position():
        # convert GMS time to UTC time in order to have a friendly date and time
        gpstime = [convert_GMS_GWk_to_UTC_time(df.GWk.values[i],df.GMS.values[i]) for i in range(len(df))]
        df['GPS_time'] = gpstime
        # convert GPS_time to new unix column in order to do interpolation on LLH date and time
        df['GPS_time'] = pd.to_datetime(df['GPS_time'])
        df['datetime_unix'] = df['GPS_time'].values.astype('int64')

        # import LLH
        csv_llh = pd.read_csv(navigation_filepath)
        # import LLH file and match different date and time from LLH and BIN/LOG
        csv_llh["GPS_time"] = csv_llh['GPSDateStamp'] +" "+ csv_llh["GPSTimeStamp"]
        csv_llh["GPS_time"] = csv_llh["GPS_time"].str.replace("/", "-")
        # convert GPS_time to new unix column in order to do interpolation
        csv_llh['GPS_time'] = pd.to_datetime(csv_llh['GPS_time'])
        csv_llh['datetime_unix'] = csv_llh['GPS_time'].values.astype('int64')


        # interpolate BIN/LOG positions on LLH more precise positions
        df['Lat'] = np.interp(df['datetime_unix'], csv_llh['datetime_unix'], csv_llh['GPSLatitude'])
        # DEBUG !!! (MJULIEN --> Error here, columns names for longitude is not 'Lon' but 'Lng')
        #df['Lon'] = np.interp(df['datetime_unix'], csv_llh['datetime_unix'], csv_llh['GPSLongitude'])
        df['Lng'] = np.interp(df['datetime_unix'], csv_llh['datetime_unix'], csv_llh['GPSLongitude'])
        # DEBUG !!! (MJULIEN --> Add of PPK corrected values for altitude too !)
        df['Alt'] = np.interp(df['datetime_unix'], csv_llh['datetime_unix'], csv_llh['elevation'])
        # change Status in BIN/LOG dataframe according to LLH "fix" column
        df['Status'] = np.interp(df['datetime_unix'], csv_llh['datetime_unix'], csv_llh['fix'])
        df['Status'] = df['Status'].astype(int)


    
    # Filter data according to rtk fix status
    if cm.is_rtkfix():
        # case where pos come from Reach LLH
        if cm.use_llh_position():
            print('func: filter data according to PPK fix status (=1 in LLH file)')
            df = df[df.Status == 1]
        else:
            print('func: filter data according to RTK fix status (=6 in autopilot log)')
            df = df[df.Status == 6]

    # Filter data according to waypoints enabled
    if cm.filter_on_waypoints():
        print('func: filter data according to waypoint messages')
        t_start = 0
        t_stop, i_stop = 0, 0
        flag_found_first_waypoint = 0
        for i in range(0, len(dfdict_dump_mavlog['MSG'])):
            # find start of the mission, i.e. first waypoint reached
            if (flag_found_first_waypoint == 0) : 
                if 'Reached waypoint' in dfdict_dump_mavlog['MSG'].Message.values[i].strip():
                    t_start = float(dfdict_dump_mavlog['MSG'].TimeUS.values[i])
                    flag_found_first_waypoint = 1
                    print("func: We'll start the mission at : ",  dfdict_dump_mavlog['MSG'].Message.values[i].strip())
            # find end of the mission  , i.e. last waypoint reached     
            if 'Reached waypoint' in dfdict_dump_mavlog['MSG'].Message.values[i].strip():
                t_stop, i_stop = float(dfdict_dump_mavlog['MSG'].TimeUS.values[i]), i
        print("func: We'll end the mission at : ",  dfdict_dump_mavlog['MSG'].Message.values[i_stop].strip())      

        if (t_start != 0):
                df = df[df.TimeUS > t_start]
        else:
            print('func: [warning] no valid tstart calculated, filter cancelled')
            
        if (t_stop != 0):
            df = df[df.TimeUS < t_stop]
        else:
            print('[warning] no valid tstop calculated, filter cancelled')
    
    # Filter data according to filter_after_waypoints
    filt_exclude_specific_datetimeUnix = []
    if len(cm.get_filt_exclude_specific_timeUS()) != 0:
        timestamp_key = "datetime_unix" if "datetime_unix" in df else "timestamp"
        factor_to_nanosaconds = 1.0 if "datetime_unix" in df else 1e9
        for t_start, t_stop in cm.get_filt_exclude_specific_timeUS():
            if t_start > t_stop:
                print(f"/!\\ t_start ({t_start}) > t_stop ({t_stop}) : Aborting filter on this interval/!\\")
                continue
            print(f'func: filter data - Removing timeUS interval {t_start} - {t_stop}')
            dfa = df[df.TimeUS < t_start]
            dfb = df[df.TimeUS > t_stop]

            v1 = int((dfa[timestamp_key].iloc[-1] if len(dfa[timestamp_key]) else df[timestamp_key].iloc[0]) * factor_to_nanosaconds)
            v2 = int((dfb[timestamp_key].iloc[0] if len(dfb[timestamp_key]) else df[timestamp_key].iloc[-1]) * factor_to_nanosaconds)

            df = pd.concat([dfa, dfb])

            filt_exclude_specific_datetimeUnix.append([v1, v2])

    print('func: Convert lat and long to UTM coordinates (pyproj)')
    projzone = cm.get_utm_zone()
    projellps = cm.get_utm_ellips() 
    projsouth = cm.get_utm_south() 
    
    print(f'func: UTM zone: {projzone}, south: {projsouth}, ellips: {projellps}')

    #Building projection from WGS84 to utm 40
    wgs2utm = pyproj.Proj(proj='utm', zone=projzone, ellps=projellps, south=projsouth)
    utm_x,utm_y=wgs2utm(np.array(df.Lng),np.array(df.Lat))
    df['X_utm'] = utm_x
    df['Y_utm'] = utm_y
    

    gpstime = [convert_GMS_GWk_to_UTC_time(df.GWk.values[i],df.GMS.values[i]) for i in range(len(df))]
    df['GPS_time'] = gpstime

    # time func execution
    print('func: exec time --> ', datetime.now() - texec)
    
    return df, filt_exclude_specific_datetimeUnix

def calc_att_at_gps_coord(df_bathy: pd.DataFrame, df_att: pd.DataFrame, att_max_angle: int) -> pd.DataFrame:
    # time func execution
    texec = datetime.now()
    
    print('func: bathy > build interpolator with ATT data')
    # Building linear interpolator for altitude (from IDOcean sources)
    # arr_att is a np aray with TimeUS, Roll, Pitch, Yaw as columns
    arr_att = df_att[['TimeUS','Roll','Pitch','Yaw']].to_numpy(dtype='float32')
    attitude_itp = interp1d(arr_att[:,0],np.rad2deg(np.unwrap(np.deg2rad(arr_att[:,1::]),axis=0)),axis=0,fill_value='extrapolate')
    
    print('func: bathy > Estimate attitude at gps position')
    
    nbpt = len(df_bathy.TimeUS)
    attestim = np.ones((nbpt,3))
    attestim_center = np.ones((nbpt,3))
    for i in range(0,nbpt):
        t = df_bathy.TimeUS.values[i]
        attestim[i] = attitude_itp(t)
        attestim_center[i] = np.mod(attestim[i] + np.array([180, 180, 0]), 360) - np.array([180, 180, 0])  # Putting roll/pitch in [-180,180] and yaw in [0,360]
    
    df_bathy['Roll']  = attestim[:,0]
    df_bathy['Pitch'] = attestim[:,1]
    df_bathy['Yaw']   = attestim[:,2]
    df_bathy['Roll_center']  = attestim_center[:,0]
    df_bathy['Pitch_center'] = attestim_center[:,1]
    df_bathy['Yaw_center']   = attestim_center[:,2]

    
    print('func: bathy > Compute attitude deviation index')
    
    
    print('func: bathy > att max angle (deg) :')
    print(att_max_angle , ' --> att index = max(picth,roll)/att_max_angle ')
    
    nbpt = len(df_bathy.TimeUS)
    attind = np.ones((nbpt, 1))
    for i in range(0, nbpt):
        curr_angle = np.max([np.abs(df_bathy.Roll_center.values[i]),
                             np.abs(df_bathy.Pitch_center.values[i])])
    
        attind[i] = curr_angle / att_max_angle
    
    df_bathy['Att_index'] = attind[:, 0]
    
    print('func: bathy > Remove points with attitude index > 1')
    
    df_bathy = df_bathy[df_bathy.Att_index < 1]
    
    # time func execution
    print('func: exec time --> ', datetime.now() - texec)
    
    return df_bathy

# Building median filter for depth (from IDOcean)
def depth_med(depth_array, time_tree, time, radius, valid_prop, depth_range):
    radius_indices=time_tree.query_ball_point([time], radius)
    values = depth_array[radius_indices, 1]
    inliers = np.where(np.logical_and(values > depth_range[0], values < depth_range[1]))[0]  # Valid depth values
    if len(inliers) <= valid_prop * len(values):  # Removing point (value -1) if not enough depth values are valid
        return (-1)
    else:  # Otherwise compute median of valid depths
        return (np.median(values[inliers]))

def calc_raw_depth_at_gps_coord(df_bathy: pd.DataFrame, df_dpth: pd.DataFrame, cm: ConfigManager) -> pd.DataFrame:
    # time func execution
    texec = datetime.now()

    dpth_med_time_win_us = cm.get_bathy_dpth_win_s() * 1e6
    dpth_med_lim_m = [cm.get_bathy_depth_min(), cm.get_bathy_depth_max()]
    dpth_med_valid_prop = cm.get_bathy_dpth_valid_prop()

    print('func: bathy > Build kd-tree filter for depth computation')
    # arr_att is a np aray with TimeUS, Roll, Pitch, Yaw as columns
    
    # WARNING : old plancha log depth as DPTH key and column is Depth
    # arr_dpth = dfdict[dpthkey][['TimeUS','Depth']].to_numpy(dtype='float32')
    # WARNING : new plancha (body V1A and v1B) log depth as RFND key and column is Dist
    if cm.get_parse_key_depth() == 'DPTH':
        arr_dpth = df_dpth[['TimeUS','Depth']].to_numpy(dtype='float32')
    else:
        arr_dpth = df_dpth[['TimeUS','Dist']].to_numpy(dtype='float32')

    # Check if echo sounder launch
    if sum(arr_dpth[:, 1]) == 0:
        raise NameError("/!\\ ECHO sonder doesn't launch /!\\")

    # build time tree for kd median filter    
    time_tree=KDTree(arr_dpth[:,0,None])
    
    print('func: bathy > Median filter param : time win (s) , dpth range (m), valid prop')
    print(dpth_med_time_win_us*1e-6, dpth_med_lim_m, dpth_med_valid_prop )

    nbpt = len(df_bathy.TimeUS)
    dpthestim = np.ones((nbpt,1))
    for i in range(0,nbpt):
        t = df_bathy.TimeUS.values[i]
        dpthestim[i]=depth_med(arr_dpth,time_tree,t,
                               dpth_med_time_win_us,
                               dpth_med_valid_prop,
                               dpth_med_lim_m)
        
    df_bathy['Depth']  = -dpthestim[:,0]
    
    print('func: bathy > Remove points with depth = -1 (bad values)')

    df_bathy = df_bathy[df_bathy.Depth != 1]
    
    # time func execution
    print('func: exec time --> ', datetime.now() - texec)
    
    return df_bathy

def build_geoid_interpolator_from_csv(cm: ConfigManager):
    dfgeoid = pd.read_csv(cm.get_geoid_path())
    # clean geoid file
    dfgeoid = dfgeoid[dfgeoid.alt < 1000.0]
    dfgeoid = dfgeoid[dfgeoid.alt > -1000.0]
    # Convert lat to utm
    wgs2utm = pyproj.Proj(proj='utm', zone=cm.get_utm_zone(), ellps=cm.get_utm_ellips(),south=cm.get_utm_south())
    x, y = wgs2utm(np.array(dfgeoid.lng),np.array(dfgeoid.lat),inverse=False)
    # compute scipy ND interpolator
    xy = np.array((x,y)).T
    z = np.array(dfgeoid['alt'])
    geoid_itp = LinearNDInterpolator(xy,z)
    return geoid_itp

def calc_ign_depth_at_gps_coord(df_bathy: pd.DataFrame, cm: ConfigManager) -> pd.DataFrame:
    # time func execution
    texec = datetime.now()
    
    utm_x_corr_list, utm_y_corr_list = [], []
    depth_ign_list, geoid_alt_list = [], []
    
    print('func: bathy > Computing pos and depth correction')
    
    if cm.use_geoid():
        print('func: bathy > Will compensate depth with gps alt and geoid grid')
        geoid_itp = build_geoid_interpolator_from_csv(cm)
    else:
        print('func: bathy > [warning] Depth not compensated with geoid and gps alt')
    
    for ind, row in df_bathy.iterrows():
    
        depthcorr = cm.get_dpth_coeff() * row.Depth
        
        # Vector that goes from the gps to the detected point on the ground
        vect_gps2pt=[cm.get_off_ant_beam_x(),
                     cm.get_off_ant_beam_y(),
                     cm.get_off_ant_beam_z()+depthcorr]
        
        # Rotating the vector according to attitude to get its coordinates in a global coordinate sytem
        # with X facing North and Y facing West
        rollrad  = np.deg2rad(row.Roll)
        pitchrad = np.deg2rad(row.Pitch)
        yawrad   = np.deg2rad(row.Yaw)
        rot_vect_gps2pt = np.dot(t3d.euler.euler2mat(-rollrad,-pitchrad,-yawrad,axes='sxyz'),vect_gps2pt)
        
        hauteur = row.Alt
        utm_x   = row.X_utm
        utm_y   = row.Y_utm
        
        # Correcting the position using rotated vector
        utm_x_corr = utm_x - rot_vect_gps2pt[1]
        utm_y_corr = utm_y + rot_vect_gps2pt[0]
        
        #! FIXME rot_vect_gps2pt est l'altitude de la planche. Si on est pas en ppk ni en rtk, il ne faut pas utiliser cette valeur car elle est abérante
        if cm.use_geoid():
            # Computing geoid altitude at corrected position
            geoid_alt = geoid_itp([utm_x_corr,utm_y_corr])[0]
            #print([utm_x_corr,utm_y_corr],geoid_alt)
            #Calcutating ign depth using rotated vector and geoid altitude
            depth_ign = hauteur+rot_vect_gps2pt[2]-geoid_alt
        else:
            # setting geoid altitude to zero, still including GPS altitude (var "hauteur")
            geoid_alt = 0 
            #Calcutating ign depth using rotated vector and geoid altitude
            depth_ign = hauteur+rot_vect_gps2pt[2]-geoid_alt
        
        utm_x_corr_list.append(utm_x_corr)
        utm_y_corr_list.append(utm_y_corr)
        depth_ign_list.append(depth_ign)
        geoid_alt_list.append(geoid_alt)
    
    df_bathy['X_utm_corr'] = utm_x_corr_list
    df_bathy['Y_utm_corr'] = utm_y_corr_list
    df_bathy['Depth_corr'] = depth_ign_list
    df_bathy['Geoid_alt']  = geoid_alt_list
    
    projzone = cm.get_utm_zone()
    projellps = cm.get_utm_ellips()
    projsouth = cm.get_utm_south()
    
    print(f'func: UTM zone: {projzone}, south: {projsouth}, ellips: {projellps}')
    #Building projection from WGS84 to utm 40
    wgs2utm = pyproj.Proj(proj='utm', zone=projzone, ellps=projellps, south=projsouth)
    lon, lat = wgs2utm(np.array(df_bathy.X_utm_corr),np.array(df_bathy.Y_utm_corr),inverse=True)
    df_bathy['Lat_corr'] = lat
    df_bathy['Lng_corr'] = lon
    
    # time func execution
    print('func: exec time --> ', datetime.now() - texec)
    
    return df_bathy

def gen_gridded_depth_data(df_bathy: pd.DataFrame, cm: ConfigManager) -> pd.DataFrame:
    # time func execution
    texec = datetime.now()

    spacing_m = cm.get_mesh_spacing_m()
    
    utm_mesh_bounds = [np.min(df_bathy.X_utm_corr),np.max(df_bathy.X_utm_corr),
                       np.min(df_bathy.Y_utm_corr),np.max(df_bathy.Y_utm_corr)]
    
    latlon_mesh_bounds = [np.min(df_bathy.Lat_corr),np.max(df_bathy.Lat_corr),
                          np.min(df_bathy.Lng_corr),np.max(df_bathy.Lng_corr)]
    
    xi = np.arange(utm_mesh_bounds[0],utm_mesh_bounds[1],spacing_m)
    yi = np.arange(utm_mesh_bounds[2],utm_mesh_bounds[3],spacing_m)
    xi, yi = np.meshgrid(xi,yi)
    
    print('func: bathy > generate meshgrid (rw x col, lat/lon bounds) :')
    print(len(xi),'x',len(xi.T),latlon_mesh_bounds)
    
    # interpolate
    x = np.array(df_bathy.X_utm_corr)
    y = np.array(df_bathy.Y_utm_corr)
    z = np.array(df_bathy.Depth_corr)
    zi = griddata((x,y),z,(xi,yi),method = cm.get_mesh_method())
    
    # shape gridded data to vectors
    xi = xi.reshape(xi.size,1)
    yi = yi.reshape(yi.size,1)
    zi = zi.reshape(zi.size,1)
    
    projzon  = cm.get_utm_zone()
    projellps = cm.get_utm_ellips()
    projsouth = cm.get_utm_south()
    
    print(f'func: UTM zone: {projzon}, south: {projsouth}, ellips: {projellps}')
    #Building projection from WGS84 to utm 40
    wgs2utm = pyproj.Proj(proj='utm', zone=projzon, ellps=projellps, south=projsouth)
    loni, lati = wgs2utm(xi,yi,inverse=True)
       
    df_gridded = pd.DataFrame(np.hstack((xi,yi,zi,lati,loni)),
                              columns=['X_utm_corr','Y_utm_corr','Depth_corr',
                                       'Lat_corr','Lng_corr'])
    
    # suppress values that are 'nan' and reset index
    df_gridded = df_gridded[np.logical_not(np.isnan(df_gridded.Depth_corr))]
    df_gridded = df_gridded.reset_index(drop=True)
    
    # time func execution
    print('func: exec time --> ',datetime.now() - texec)
    
    return df_gridded

def plot_basic_bathy_data_time(df_bathy: pd.DataFrame, bathy_path: Path, fname: str = '0') -> None:
   
    fig = plt.figure()
    ax0 = fig.add_subplot(311)
    df_bathy.plot.line(x='TimeUS',y=['Att_index'],
                 ax=ax0,grid=True)
    ax1 = fig.add_subplot(312,sharex=ax0)
    df_bathy.plot.line(x='TimeUS',y=['Alt','Geoid_alt'],
                 ax=ax1,grid=True)
    ax2 = fig.add_subplot(313,sharex=ax0)
    df_bathy.plot.line(x='TimeUS',y=['Depth','Depth_corr'],
                 ax=ax2,grid=True)
    
    sizes_inches = 12
    figpath = Path(bathy_path, f'attitude_depth_timeplot_{fname}.png')
    fig.set_size_inches(sizes_inches,sizes_inches)
    fig.savefig(figpath,dpi=600)

def plot_basic_bathy_data_2D(df_bathy: pd.DataFrame, bathy_path: Path, fname: str = '0') -> None:
    
    fig2d = plt.figure()
    ax2d = fig2d.add_subplot(111)
    df_bathy.plot.scatter(x='X_utm_corr',y='Y_utm_corr',c='Depth_corr',
                    ax=ax2d, colormap='viridis')
    ax2d.axes.set_aspect('equal')
    ax2d.grid()
    
    sizes_inches = 12
    figpath = Path(bathy_path, f'depth_samples_utmcoord_{fname}.png')
    fig2d.set_size_inches(sizes_inches,sizes_inches)
    fig2d.savefig(figpath,dpi=600)

def bathy_preproc_to_txt(bathy_preproc_path: Path) -> Path:
    # Inputs :
    # 1.bathy_preproc = path of the bathy_preproc file 
    
    # Outputs :
    # 1.txt_path = path of the txt file, which can be used by exiftool functions
    # The function saves a txt file with the same information of the bathy_preproc file in the same directory
    
    # get CSV file name and replace .CSV by .txt
    txt_file_name = "exiftool_tags.txt"
    csv_file_name = txt_file_name.replace("txt", "csv")
    txt_path = Path(bathy_preproc_path.parent, f"{bathy_preproc_path.stem}_{txt_file_name}")
    csv_path = Path(bathy_preproc_path.parent, f"{bathy_preproc_path.stem}_{csv_file_name}")
    
    # open bathy_preproc file 
    bathy_preproc_df = pd.read_csv(bathy_preproc_path)
    # Note exiftool : GPSPitch and GPSRoll are not standard tags, and must be user-defined.
    bathy_preproc_df = bathy_preproc_df[['GPS_time', 'Lat', 'Lng', 'Depth', 'Roll', 'Pitch', 'Yaw']]
    # rename columns
    # N.B. Yaw is stored in the XMP-exif:GPSTrack tag
    bathy_preproc_df.rename(columns={'Lat': 'GPSLatitude', 'Lng': 'GPSLongitude', 'Depth': 'GPSAltitude', 'Roll': 'GPSRoll', 'Pitch': 'GPSPitch', 'Yaw': 'GPSTrack'}, inplace=True)
    # split GPS DATE & TIME in GPSDATE & GPSTIME
    bathy_preproc_df[['GPSDateStamp', 'GPSTimeStamp']] = bathy_preproc_df['GPS_time'].str.split(expand=True)
    # write the TXT file for Geotag
    bathy_preproc_df.to_csv(txt_path, index = False, sep=',', mode='a')
    # write the CSV file for Roll, Pitch
    bathy_preproc_df.to_csv(csv_path, index = False)
    return csv_path