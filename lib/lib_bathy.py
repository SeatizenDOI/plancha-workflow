# -*- coding: utf-8 -*-
"""
Created on Tue Mar 15 12:17:30 2022

@author: mjulien
"""
import os
import csv
import json
import pyproj 
import shutil 
import platform
import subprocess
import numpy as np
import pandas as pd
import datetime as dt
import geopandas as gpd
import transforms3d as t3d 
from functools import partial
import matplotlib.pyplot as plt
from shapely.geometry import Point

from scipy.spatial import KDTree
from scipy.interpolate import interp1d, LinearNDInterpolator, griddata

from geocube.api.core import make_geocube
from geocube.rasterize import rasterize_points_griddata

from lib.lib_folium_maps import *
from lib.lib_open3d_model import *

def clean_nullbyte_raw_log(log_path):
    # time func execution
    shutil.copy(log_path,log_path+'.bkp')
    with open(log_path, 'rb') as myfile:
        data = myfile.read()
        nullcnt = data.count( b'\x00' )
        print('... found',nullcnt,' NULL bytes')
    if nullcnt:
        with open(log_path, 'rb') as myfile:
            print('... parsing')
            data = myfile.readlines()
            with open(log_path+'.tmp', 'w') as of:
                print('... cleaning')
                for line in data:
                    strline = line.decode("utf-8")[:-1]
                    of.write(strline.replace('\x00', ''))
            with open(log_path+'.tmp', 'rb') as myfile:
                print('... checking')
                data = myfile.read()
                nullcnt = data.count( b'\x00' )
                print('... found',nullcnt,' NULL bytes in new file copy')
            shutil.move( log_path+'.tmp', log_path )
    return True

def parse_raw_log(log_path,cfg_prog):
    # time func execution
    texec = dt.datetime.now()
    
    print('Cleaning raw log ...')
    clean_nullbyte_raw_log(log_path,cfg_prog)
    
    cfg_parse = cfg_prog['parse']
    
    # Status list (fixed)
    # DEBUG !!! (MJULIEN --> Suppres MSG from parsed lines, causes bug on some log files)
    # status_list=['MODE','ARM']
    status_list=['MODE','ARM','MSG']
    
    # Read mandatory params from config dict
    param_list=[cfg_parse['gpskey'] , # mandatory
                cfg_parse['attkey'] , # mandatory
                cfg_parse['dpthkey'], # mandatory
                ]
    # Read optional params from config dict. Strip and split string in case of multiple params
    param_list.extend(cfg_parse['optkey'].strip().split(','))
    
    # init buffers
    datadict={}
    headdict={}
    dfdict  ={}
    for param in param_list:
        datadict[param] = []
        headdict[param] = []
        dfdict[param]   = []
    for status in status_list:
        datadict[status] = []
        headdict[status] = []
        dfdict[status]   = []
    
    
    #Parsing the log file
    print('func: parsing log for keys:')
    print(param_list,status_list)
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
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return dfdict

def parse_raw_bin(log_path,cfg_prog):
    # time func execution
    texec = dt.datetime.now()
    
    cfg_parse = cfg_prog['parse']
    
    # Status list (fixed)
    status_list=['MODE','ARM','MSG']
    
    # Read mandatory params from config dict
    param_list=[cfg_parse['gpskey'] , # mandatory
                cfg_parse['attkey'] , # mandatory
                cfg_parse['dpthkey'], # mandatory
                ]
    # Read optional params from config dict. Strip and split string in case of multiple params
    opt = cfg_parse['optkey'].strip().split(',')
    if len(opt) > 0 and opt[0] != '':
        param_list.extend(opt)
    
    # init buffers
    dfdict  ={}
    for param in param_list:
        dfdict[param]   = []
    for status in status_list:
        dfdict[status]   = []
    
    #Parsing the bin file
    print('func: parsing log for keys:')
    print(param_list,status_list)
    
    filebuf = './tmp.csv'
    for p in param_list:
        print('Reading data for entry:',p)
        tmp_cmd = "python ./lib/mavlogdump.py --planner --format csv --type "+p+" "+log_path+" > "+filebuf
        # print(tmp_cmd)
        # if platform.system() == 'Windows':
        #     tmp_cmd=tmp_cmd.replace('/','\\')
        subprocess.call(tmp_cmd, shell=True)
        dfdict[p] = pd.read_csv(filebuf, sep=";")
        print('found',len(dfdict[p]),'points')
        os.remove(filebuf)
    for p in status_list:
        tmp_cmd = "python ./lib/mavlogdump.py --planner --format csv --type "+p+" "+log_path+" > "+filebuf
        # print(tmp_cmd)
        # if platform.system() == 'Windows':
        #     tmp_cmd=tmp_cmd.replace('/','\\')
        subprocess.call(tmp_cmd, shell=True)
        dfdict[p] = pd.read_csv(filebuf, sep=";")
        os.remove(filebuf)
        
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)

    return dfdict

def convert_GMS_GWk_to_UTC_time(gpsweek,gpsseconds,leapseconds=0):
    import datetime
    datetimeformat = "%Y-%m-%d %H:%M:%S.%f"
    epoch = datetime.datetime.strptime("1980-01-06 00:00:00.000",datetimeformat)
    elapsed = datetime.timedelta(days=int((gpsweek*7)),seconds=int(gpsseconds+leapseconds))
    return datetime.datetime.strftime(epoch + elapsed,datetimeformat)

def build_dataframe_gps(dfdict,cfg_prog, TXT_PATH):
    # time func execution
    texec = dt.datetime.now()
    
    key = cfg_prog['parse']['gpskey']
    df = dfdict[key].copy()

    print('func: initial dataframe has',len(df),'points')

    # use LLH position instead of the LOG/BIN one
    if cfg_prog['gps']['use_llh_position'] :
        # convert GMS time to UTC time in order to have a friendly date and time
        cfg_gps = cfg_prog['gps']
        gpstime = [convert_GMS_GWk_to_UTC_time(df.GWk.values[i],df.GMS.values[i]/1000.0) for i in range(len(df))]
        df['GPS_time'] = gpstime
        # convert GPS_time to new unix column in order to do interpolation on LLH date and time
        df['GPS_time'] = pd.to_datetime(df['GPS_time'])
        df['datetime_unix'] = df['GPS_time'].values.astype('int64')

        # import LLH
        csv_llh = pd.read_csv(TXT_PATH)
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

    cfg_gps = cfg_prog['gps']
    
    # Filter data according to rtk fix status
    if cfg_gps['filt_rtkfix'] == True :
        # case where pos come from Reach LLH
        if cfg_prog['gps']["use_llh_position"] == True:
            print('func: filter data according to PPK fix status (=1 in LLH file)')
            df = df[df.Status == 1]
        # case where pos come from Reach LLH
        if cfg_prog['gps']["use_llh_position"] == False:
            print('func: filter data according to RTK fix status (=6 in autopilot log)')
            df = df[df.Status == 6]

    # Filter data according to waypoints enabled ?
    if cfg_gps['filt_waypoint'] == True :
        print('func: filter data according to waypoint messages')
        t_start = 0
        t_stop, i_stop = 0, 0
        flag_found_first_waypoint = 0
        for i in range(0, len(dfdict['MSG'])):
            # find start of the mission, i.e. first waypoint reached
            if (flag_found_first_waypoint == 0) : 
                if 'Reached waypoint' in dfdict['MSG'].Message.values[i].strip():
                    t_start = float(dfdict['MSG'].TimeUS.values[i])
                    flag_found_first_waypoint = 1
                    print("func: We'll start the mission at : ",  dfdict['MSG'].Message.values[i].strip())
            # find end of the mission  , i.e. last waypoint reached     
            if 'Reached waypoint' in dfdict['MSG'].Message.values[i].strip():
                t_stop, i_stop = float(dfdict['MSG'].TimeUS.values[i]), i
        print("func: We'll end the mission at : ",  dfdict['MSG'].Message.values[i_stop].strip())      

        if (t_start != 0):
                df = df[df.TimeUS > t_start]
        else:
            print('func: [warning] no valid tstart calculated, filter cancelled')
            
        if (t_stop != 0):
            df = df[df.TimeUS < t_stop]
        else:
            print('[warning] no valid tstop calculated, filter cancelled')
    
    # Filter data according to filter_after_waypoints
    if len(cfg_gps['filt_exclude_specific_timeUS']) != 0:
        for t_start, t_stop in cfg_gps['filt_exclude_specific_timeUS']:
            if t_start > t_stop:
                print("/!\\ t_start ({}) > t_stop ({}) : Aborting filter on this interval/!\\".format(t_start, t_stop))
                continue
            print('func: filter data - Removing timeUS interval {} - {}'.format(t_start, t_stop))
            dfa = df[df.TimeUS < t_start]
            dfb = df[df.TimeUS > t_stop]
            df = pd.concat([dfa, dfb])

        

    print('func: Convert lat and long to UTM coordinates (pyproj)')
    
    projzone  = cfg_gps['utm_zone']
    projellps = cfg_gps['utm_ellips'] 
    projsouth = cfg_gps['utm_south']
    
    print(f'func: UTM zone: {projzone}, south: {projsouth}, ellips: {projellps}')

    #Building projection from WGS84 to utm 40
    wgs2utm = pyproj.Proj(proj='utm', zone=projzone, ellps=projellps,south=projsouth)
    utm_x,utm_y=wgs2utm(np.array(df.Lng),np.array(df.Lat))
    df['X_utm'] = utm_x
    df['Y_utm'] = utm_y
    
    gpstime = [convert_GMS_GWk_to_UTC_time(df.GWk.values[i],df.GMS.values[i]/1000.0) for i in range(len(df))]
    df['GPS_time'] = gpstime
    
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return df

def calc_att_at_gps_coord(df,dfdict,cfg_prog):
    # time func execution
    texec = dt.datetime.now()
        
    attkey = cfg_prog['parse']['attkey']
    att_max_angle = cfg_prog['bathy']['max_angle']
    
    print('func: bathy > build interpolator with ATT data')
    # Building linear interpolator for altitude (from IDOcean sources)
    # arr_att is a np aray with TimeUS, Roll, Pitch, Yaw as columns
    arr_att = dfdict[attkey][['TimeUS','Roll','Pitch','Yaw']].to_numpy(dtype='float32')
    attitude_itp=interp1d(arr_att[:,0],np.rad2deg(np.unwrap(np.deg2rad(arr_att[:,1::]),axis=0)),axis=0,fill_value='extrapolate')
    
    print('func: bathy > Estimate attitude at gps position')
    
    nbpt = len(df.TimeUS)
    attestim = np.ones((nbpt,3))
    attestim_center = np.ones((nbpt,3))
    for i in range(0,nbpt):
        t = df.TimeUS.values[i]
        attestim[i] = attitude_itp(t)
        attestim_center[i] = np.mod(attestim[i] + np.array([180, 180, 0]), 360) - np.array([180, 180, 0])  # Putting roll/pitch in [-180,180] and yaw in [0,360]
    
    df['Roll']  = attestim[:,0]
    df['Pitch'] = attestim[:,1]
    df['Yaw']   = attestim[:,2]
    df['Roll_center']  = attestim_center[:,0]
    df['Pitch_center'] = attestim_center[:,1]
    df['Yaw_center']   = attestim_center[:,2]

    
    print('func: bathy > Compute attitude deviation index')
    
    
    print('func: bathy > att max angle (deg) :')
    print(att_max_angle , ' --> att index = max(picth,roll)/att_max_angle ')
    
    nbpt = len(df.TimeUS)
    attind = np.ones((nbpt,1))
    for i in range(0,nbpt):
        curr_angle = np.max([np.abs(df.Roll_center.values[i]),
                             np.abs(df.Pitch_center.values[i])])
    
        attind[i] = curr_angle/att_max_angle
    
    df['Att_index']  = attind[:,0]
    
    print('func: bathy > Remove points with attitude index > 1')
    
    df = df[df.Att_index < 1]
    
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return df

#Building median filter for depth (from IDOcean)
def depth_med(depth_array, time_tree, time, radius, valid_prop, depth_range):
    radius_indices=time_tree.query_ball_point([time], radius)
    values = depth_array[radius_indices, 1]
    inliers = np.where(np.logical_and(values > depth_range[0], values < depth_range[1]))[0]  # Valid depth values
    if len(inliers) <= valid_prop * len(values):  # Removing point (value -1) if not enough depth values are valid
        return (-1)
    else:  # Otherwise compute median of valid depths
        return (np.median(values[inliers]))

def calc_raw_depth_at_gps_coord(df,dfdict,cfg_prog):
    # time func execution
    texec = dt.datetime.now()

    dpthkey = cfg_prog['parse']['dpthkey']
    dpth_med_time_win_us = cfg_prog['bathy']['dpth_win_s']*1e6
    dpth_med_lim_m = [cfg_prog['bathy']['dpth_range']['min'],cfg_prog['bathy']['dpth_range']['max']]
    dpth_med_valid_prop = cfg_prog['bathy']['dpth_valid_prop']

    print('func: bathy > Build kd-tree filter for depth computation')
    # arr_att is a np aray with TimeUS, Roll, Pitch, Yaw as columns
    
    # WARNING : old plancha log depth as DPTH key and column is Depth
    # arr_dpth = dfdict[dpthkey][['TimeUS','Depth']].to_numpy(dtype='float32')
    # WARNING : new plancha (body V1A and v1B) log depth as RFND key and column is Dist
    if dpthkey == 'DPTH':
        arr_dpth = dfdict[dpthkey][['TimeUS','Depth']].to_numpy(dtype='float32')
    else:
        arr_dpth = dfdict[dpthkey][['TimeUS','Dist']].to_numpy(dtype='float32')

    # Check if echo sounder launch
    if sum(arr_dpth[:, 1]) == 0:
        raise NameError("/!\\ ECHO sonder doesn't launch /!\\")

    # build time tree for kd median filter    
    time_tree=KDTree(arr_dpth[:,0,None])
    
    print('func: bathy > Median filter param : time win (s) , dpth range (m), valid prop')
    print(dpth_med_time_win_us*1e-6, dpth_med_lim_m, dpth_med_valid_prop )
    
   
    nbpt = len(df.TimeUS)
    dpthestim = np.ones((nbpt,1))
    for i in range(0,nbpt):
        t = df.TimeUS.values[i]
        dpthestim[i]=depth_med(arr_dpth,time_tree,t,
                               dpth_med_time_win_us,
                               dpth_med_valid_prop,
                               dpth_med_lim_m)
    
    df['Depth']  = -dpthestim[:,0]
    
    print('func: bathy > Remove points with depth = -1 (bad values)')

    df = df[df.Depth != 1]
    
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return df

def build_geoid_interpolator_from_csv(cfg_prog):
    dfgeoid = pd.read_csv(cfg_prog['bathy']['geoid_path'])
    # clean geoid file
    dfgeoid = dfgeoid[dfgeoid.alt < 1000.0]
    dfgeoid = dfgeoid[dfgeoid.alt > -1000.0]
    # Convert lat to utm
    projzone  = cfg_prog['gps']['utm_zone']
    projellps = cfg_prog['gps']['utm_ellips'] 
    projsouth = cfg_prog['gps']['utm_south']
    wgs2utm = pyproj.Proj(proj='utm', zone=projzone, ellps=projellps,south=projsouth)
    x, y = wgs2utm(np.array(dfgeoid.lng),np.array(dfgeoid.lat),inverse=False)
    # compute scipy ND interpolator
    xy = np.array((x,y)).T
    z = np.array(dfgeoid['alt'])
    geoid_itp = LinearNDInterpolator(xy,z)
    return geoid_itp

def calc_ign_depth_at_gps_coord(df,dfdict,cfg_prog):
    # time func execution
    texec = dt.datetime.now()
    
    cfg_bathy = cfg_prog['bathy']
    
    utm_x_corr_list = []
    utm_y_corr_list = []
    depth_ign_list = []
    geoid_alt_list = []
    
    print('func: bathy > Computing pos and depth correction')
    
    if cfg_bathy['use_geoid']==True:
        print('func: bathy > Will compensate depth with gps alt and geoid grid')
        geoid_itp = build_geoid_interpolator_from_csv(cfg_prog)
    else:
        print('func: bathy > [warning] Depth not compensated with geoid and gps alt')
    
    for ind, row in df.iterrows():
    
        depthcorr = cfg_bathy['dpth_coeff'] * row.Depth
        
        # Vector that goes from the gps to the detected point on the ground
        vect_gps2pt=[cfg_bathy['offset_ant_beam']['x'],
                     cfg_bathy['offset_ant_beam']['y'],
                     cfg_bathy['offset_ant_beam']['z']+depthcorr]
        
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
        
        if cfg_bathy['use_geoid']==True:
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
    
    df['X_utm_corr'] = utm_x_corr_list
    df['Y_utm_corr'] = utm_y_corr_list
    df['Depth_corr'] = depth_ign_list
    df['Geoid_alt']  = geoid_alt_list
    
    projzone  = cfg_prog['gps']['utm_zone']
    projellps = cfg_prog['gps']['utm_ellips'] 
    projsouth = cfg_prog['gps']['utm_south']
    
    print(f'func: UTM zone: {projzone}, south: {projsouth}, ellips: {projellps}')
    #Building projection from WGS84 to utm 40
    wgs2utm = pyproj.Proj(proj='utm', zone=projzone, ellps=projellps,south=projsouth)
    lon, lat = wgs2utm(np.array(df.X_utm_corr),np.array(df.Y_utm_corr),inverse=True)
    df['Lat_corr'] = lat
    df['Lng_corr'] = lon
    
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return df

def gen_gridded_depth_data(df,cfg_prog):
    # time func execution
    texec = dt.datetime.now()

    spacing_m = cfg_prog['mesh']['spacing_m']
    
    utm_mesh_bounds = [np.min(df.X_utm_corr),np.max(df.X_utm_corr),
                       np.min(df.Y_utm_corr),np.max(df.Y_utm_corr)]
    
    latlon_mesh_bounds = [np.min(df.Lat_corr),np.max(df.Lat_corr),
                          np.min(df.Lng_corr),np.max(df.Lng_corr)]
    
    xi = np.arange(utm_mesh_bounds[0],utm_mesh_bounds[1],spacing_m)
    yi = np.arange(utm_mesh_bounds[2],utm_mesh_bounds[3],spacing_m)
    xi, yi = np.meshgrid(xi,yi)
    
    print('func: bathy > generate meshgrid (rw x col, lat/lon bounds) :')
    print(len(xi),'x',len(xi.T),latlon_mesh_bounds)
    
    # interpolate
    x = np.array(df.X_utm_corr)
    y = np.array(df.Y_utm_corr)
    z = np.array(df.Depth_corr)
    zi = griddata((x,y),z,(xi,yi),method=cfg_prog['mesh']['method'])
    
    # shape gridded data to vectors
    xi = xi.reshape(xi.size,1)
    yi = yi.reshape(yi.size,1)
    zi = zi.reshape(zi.size,1)
    
    projzone  = cfg_prog['gps']['utm_zone']
    projellps = cfg_prog['gps']['utm_ellips'] 
    projsouth = cfg_prog['gps']['utm_south']
    
    print(f'func: UTM zone: {projzone}, south: {projsouth}, ellips: {projellps}')
    #Building projection from WGS84 to utm 40
    wgs2utm = pyproj.Proj(proj='utm', zone=projzone, ellps=projellps,south=projsouth)
    loni, lati = wgs2utm(xi,yi,inverse=True)
       
    df_gridded = pd.DataFrame(np.hstack((xi,yi,zi,lati,loni)),
                              columns=['X_utm_corr','Y_utm_corr','Depth_corr',
                                       'Lat_corr','Lng_corr'])
    
    # suppress values that are 'nan' and reset index
    df_gridded = df_gridded[np.logical_not(np.isnan(df_gridded.Depth_corr))]
    df_gridded = df_gridded.reset_index(drop=True)
    
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return df_gridded

def plot_basic_bathy_data_time(df,BATHY_PATH,fname='0'):
   
    fig = plt.figure()
    ax0 = fig.add_subplot(311)
    df.plot.line(x='TimeUS',y=['Att_index'],
                 ax=ax0,grid=True)
    ax1 = fig.add_subplot(312,sharex=ax0)
    df.plot.line(x='TimeUS',y=['Alt','Geoid_alt'],
                 ax=ax1,grid=True)
    ax2 = fig.add_subplot(313,sharex=ax0)
    df.plot.line(x='TimeUS',y=['Depth','Depth_corr'],
                 ax=ax2,grid=True)
    
    sizes_inches = 12
    figpath = BATHY_PATH + "/"
    figname = figpath+'attitude_depth_timeplot_'+fname
    fig.set_size_inches(sizes_inches,sizes_inches)
    fig.savefig(figname+'.png',dpi=600)
    
    return fig

def plot_basic_bathy_data_2D(df, BATHY_PATH,fname='0'):
    
    fig2d = plt.figure()
    ax2d = fig2d.add_subplot(111)
    df.plot.scatter(x='X_utm_corr',y='Y_utm_corr',c='Depth_corr',
                    ax=ax2d, colormap='viridis')
    ax2d.axes.set_aspect('equal')
    ax2d.grid()
    
    sizes_inches = 12
    figpath = BATHY_PATH + "/"
    figname = figpath+'depth_samples_utmcoord_'+fname    
    fig2d.set_size_inches(sizes_inches,sizes_inches)
    fig2d.savefig(figname+'.png',dpi=600)
    
    return fig2d

#%% MAIN BATHY PROCESSING

def run_bathy_analysis(cfg_prog, BATHY_PATH, TXT_PATH, SENSORS_PATH):
    
    ##### section : load data ###
    flag_log, dfdict = 0, {}
    # list log files in folder
    file_list = os.listdir(SENSORS_PATH)
    # reverse list to check .LOG before .BIN (alphabetic order)
    file_list.reverse()
    for file in file_list :
        if file.endswith("log") or file.endswith("LOG") :
            log_path = SENSORS_PATH + "/" + file
            print('\ninfo: Loadind autopilot data :', log_path)
            dfdict = parse_raw_log(log_path, cfg_prog)
            flag_log = 1
            break
        if file.endswith("bin") or file.endswith("BIN") :
            log_path = SENSORS_PATH + "/" + file
            print('\ninfo: Loadind autopilot data :', log_path)
            dfdict = parse_raw_bin(log_path, cfg_prog)
            flag_log = 1
            break
            
    if not flag_log :
        print("\ninfo: We do not have a log file, please convert the bin to log")
        return
    else:
        print("\n-- 3A of 6 : BATHIMETRY PROCESSING\n")
    
    print('\ninfo: Build base dataframe from GPS')
    
    df = build_dataframe_gps(dfdict,cfg_prog, TXT_PATH)
    
    # print('info: GPS log starts >',df.GPS_time.values[0])
    # print('info: GPS log ends   >',df.GPS_time.values[-1])
    
    print('info: number of point in main dataframe : ', len(df))
    
    ##### section : bathymetry pre-process ###
    
    print('\ninfo: Estimate attitude at GPS positions')
    
    df = calc_att_at_gps_coord(df,dfdict,cfg_prog)
    
    print('info: number of point in main dataframe : ', len(df))
    
    print('\ninfo: Estimate raw depth at GPS positions')
    
    df = calc_raw_depth_at_gps_coord(df,dfdict,cfg_prog)
    
    print('info: number of point in main dataframe : ', len(df))
    
    print('\ninfo: Correct depth values')
    df = calc_ign_depth_at_gps_coord(df,dfdict,cfg_prog)
    
    print('info: number of point in main dataframe : ', len(df))
    
    print('\ninfo: Save to file')
    
    # create folder
    if not os.path.exists(BATHY_PATH):
        os.makedirs(BATHY_PATH)
        
    # dump prog config
    filepath = cfg_prog['path']['destpath']
    with open(filepath+'prog_config.json', 'w') as fp:
        json.dump(cfg_prog, fp,indent=3)
        
    # dump processed data
    filepath = BATHY_PATH + "/"
    df.to_csv(filepath+'bathy_preproc.csv',sep=',',index=False)
    
    # dump associated metadata
    metadata = cfg_prog
    metadata['creation'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath+'bathy_preproc.csv.metadata', 'w') as fp:
        json.dump(cfg_prog, fp,indent=3)
    
    ###### section : plot data #####
    
    print('\ninfo: Plot data')
    
    fig = plot_basic_bathy_data_time(df, BATHY_PATH,'preproc')
    fig = plot_basic_bathy_data_2D(df, BATHY_PATH,'preproc')
    
    print('\ninfo: Generate interactive map')
    # generate map base layer
    fmap = folium_map_gen_sat_layer_EsriSat()
    # add scatter data (layer name have to be unique)
    fmap = folium_map_add_scatterdata(fmap,df,'depth')
    # add line data (layer name have to be unique)
    fmap = folium_map_add_linepath(fmap,df,'track')
    # Add layer control to show/hide data
    folium.LayerControl().add_to(fmap)
    
    print('\ninfo: Save interactive map')
    fmap.save(filepath + '/webmap_usv_track.html')
    
    return df



#%% 3D MODEL

def run_bathy_postprocessing(df, cfg_prog, BATHY_PATH):
    ###### section : interpolate bathy to regular grid
    # time func execution
    texec = dt.datetime.now()
    
    print('\nRunning open3D modelization...')

    # load initial data to compute average distance before generating gridded data
    print('Computing initial point cloud average distance')
    # get x, y, and z values in a numpy array
    xyz = np.array(df[['X_utm_corr','Y_utm_corr','Depth_corr']])
    # xyz = np.array(df[['Lng_corr','Lat_corr','Depth_corr']])
    # build point cloud from xyz matrix
    pcd, avgdist , stddist = build_o3d_pointcloud(xyz)
    print('stddist_rel >>>>>>',stddist)
    # gen gridded data
    print('Generating gridded data')
    cfg_prog['mesh']['spacing_m'] = np.round((avgdist+3*stddist),3)
    df_grid = gen_gridded_depth_data(df,cfg_prog)
    
    # get x, y, and z values in a numpy array
    print('Computing final point cloud and mesh')
    xyz = np.array(df_grid[['X_utm_corr','Y_utm_corr','Depth_corr']])
    # build point cloud from xyz matrix
    pcd, avgdist , _ = build_o3d_pointcloud(xyz)
    # build mesh with faces from point cloud
    mesh = build_o3d_trimesh(pcd,avgdist,method=cfg_prog['mesh']['3Dalgo'])
    
    print('Done ... open3D mesh computed')
    
    print('\ninfo: Save gridded data to csv file')

    # create folder
    if not os.path.exists(BATHY_PATH):
        os.makedirs(BATHY_PATH)
    
    # set current path vars
    filepath = BATHY_PATH + "/"
    sessiontag = cfg_prog['session_info']['session_name']

    # dump prog config
    with open(filepath+'prog_config.json', 'w') as fp:
        json.dump(cfg_prog, fp,indent=3)
    
    # set tags for file names
    tags = '{0}'.format(cfg_prog['mesh']['method'])
    
    # dump postprocessed data
    df_grid.to_csv(filepath+'bathy_postproc_'+tags+'.csv',sep=',',index=False)
    
    # dump associated metadata
    metadata = cfg_prog
    metadata['creation'] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath+'bathy_postproc_'+tags+'.csv.metadata', 'w') as fp:
        json.dump(cfg_prog, fp,indent=3)
    
    # Plot post-processed bathy data
    print('\ninfo: Generate simple plot of post-processed data')
    fig = plot_basic_bathy_data_2D(df_grid, BATHY_PATH,'postproc_'+tags)   

    # set tags for file names
    tags = '{0}'.format(cfg_prog['mesh']['method'])
    
    # Shapefile with geopandas
    print('\ninfo: Generating shapefile from gridded data')
    df_shp = df_grid[['Lng_corr','Lat_corr','Depth_corr']]
    df_shp.columns = ['lng','lat','depth']
    df_shp['geometry'] = df_shp.apply(lambda row: Point(row.lng,row.lat,row.depth),axis=1) 
    gdf = gpd.GeoDataFrame(df_shp, geometry=df_shp.geometry)
    gdf.set_crs(epsg=4326, inplace=True)
    gdf.to_file(filepath+sessiontag+'_bathy_shapefile-pointcloud-'+tags+'.shp')
    print("Shapefile created")

    # set tags for file names
    tags = '{0}'.format(cfg_prog['mesh']['method'])

    # Raster with geocube
    print('\ninfo: Generating raster from gridded data')
    resol_lng = np.median([np.abs(gdf.iloc[i].lng - gdf.iloc[i+1].lng) for i in range(len(gdf)-1)])
    resol_lat = np.median([np.abs(gdf.iloc[i].lat - gdf.iloc[i+1].lat) for i in range(len(gdf)-1)])
    resol = np.min([resol_lng, resol_lat])
    maxnbpt = 1e6
    condpt = ((np.max(gdf.lng.values)-np.min(gdf.lng.values))/resol) * ((np.max(gdf.lat.values)-np.min(gdf.lat.values))/resol)
    while condpt >= maxnbpt:
        resol = resol*1.1
        condpt = ((np.max(gdf.lng.values)-np.min(gdf.lng.values))/resol) * ((np.max(gdf.lat.values)-np.min(gdf.lat.values))/resol)
        print('reducing raster resolution, file too big otherwise ...')
    print('Done adjusting raster resolution ...')
    print('Building geocube object')
    geo_grid = make_geocube(
        vector_data=gdf,
        measurements=['depth'],
        resolution=(-resol, resol),
        rasterize_function=partial(rasterize_points_griddata, filter_nan=True,  method=cfg_prog['mesh']['method']),
    )
    print('Rasterize it')
    raster_name = sessiontag+'_bathy_raster-'+tags+'.tif'
    geo_grid["depth"].rio.to_raster(filepath+raster_name)
    print("Raster created")

    # Shapefile with countours
    print('\ninfo: Generating shapefile with contour lines from raster')
    try:
        # shapefile with countour lines polygons from raster
        tif_file = raster_name
        nb_line = 10
        z_var = 'depth' # name of columns with depth in tiff file
        interval_m = (np.max(gdf[z_var].values)-np.min(gdf[z_var].values))/nb_line
        interval_m = str(interval_m) # in meter, cast to string
        # shapzfile with contour as lines
        out_file = sessiontag+'_bathy_shapefile-contourline-'+tags+'.shp'
        gdal_cmd = 'gdal_contour -b 1 -a '+z_var+' -i '+interval_m+' '+filepath+tif_file+' '+filepath+out_file
        if platform.system() == 'Windows':
                gdal_cmd=gdal_cmd.replace('/','\\')
        print('gdal cmd:',gdal_cmd)
        os.system(gdal_cmd)
        # shapzfile with contour as filled polygon
        out_file = sessiontag+'_bathy_shapefile-contourpoly-'+tags+'.shp'
        gdal_cmd = 'gdal_contour -b 1 -p -i '+interval_m+' -amax '+z_var+' '+filepath+tif_file+' '+filepath+out_file
        if platform.system() == 'Windows':
                gdal_cmd=gdal_cmd.replace('/','\\')
        print('gdal cmd:',gdal_cmd)
        os.system(gdal_cmd)
    except:
        print('\n--- WARNING ---')
        print('Problem occurs when generating shapefile with countours with gdal. Done nothing ...')
    print('Done ...')
    
    # set tags for file names
    tags = '{0}-{1}'.format(cfg_prog['mesh']['method'],
                            cfg_prog['mesh']['3Dalgo'])

    # Write 3D object to .ply file
    print('\ninfo: Writing current shapes to ply file in :',filepath)
    o3d.io.write_triangle_mesh(filepath+sessiontag+'_bathy_3dmodel-'+tags+'.ply', mesh, write_ascii=True)
    
    # time func execution
    print('func: exec time --> ',dt.datetime.now() - texec)
    
    return df_grid

def bathy_preproc_to_txt(bathy_preproc_path) :
    # Inputs :
    # 1.bathy_preproc = path of the bathy_preproc file 
    
    # Outputs :
    # 1.txt_path = path of the txt file, which can be used by exiftool functions
    # The function saves a txt file with the same information of the bathy_preproc file in the same directory
    
    # get CSV file name and replace .CSV by .txt
    bathy_preproc_file_name = os.path.basename(os.path.normpath(bathy_preproc_path))
    #txt_file_name = bathy_preproc_file_name.replace("csv", "txt")
    txt_file_name = "exiftool_tags.txt"
    csv_file_name = txt_file_name.replace("txt", "csv")
    txt_path = bathy_preproc_path.replace(bathy_preproc_file_name, txt_file_name)
    csv_path = bathy_preproc_path.replace(bathy_preproc_file_name, csv_file_name)
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