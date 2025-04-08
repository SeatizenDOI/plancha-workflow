import folium
import traceback
import subprocess
import numpy as np
import pandas as pd
import open3d as o3d
import geopandas as gpd
from pathlib import Path
from shapely import Point
from functools import partial
from natsort import natsorted
from datetime import datetime
from geocube.api.core import make_geocube
from geocube.rasterize import rasterize_points_griddata

from .ConfigManager import ConfigManager

from .lib.lib_tools import generate_theoric_waypoints_file, write_real_mission_interval, replace_comma_by_dot
from .lib.lib_bathy import parse_raw_bin, parse_raw_log, build_dataframe_gps, calc_att_at_gps_coord, \
    calc_raw_depth_at_gps_coord, calc_ign_depth_at_gps_coord, plot_basic_bathy_data_time, plot_basic_bathy_data_2D, \
    gen_gridded_depth_data
from .lib.lib_folium_maps import folium_map_gen_sat_layer_EsriSat, folium_map_add_scatterdata, folium_map_add_linepath
from .lib.lib_open3d_model import build_o3d_pointcloud, build_o3d_trimesh

class BathyManager:
    
    def __init__(self, sensors_path: Path, bathy_path: Path):
        self.sensors_path = sensors_path
        self.bathy_path = bathy_path

        self.filt_exclude_specific_datetimeUnix = []

        self.df_bathy = pd.DataFrame()
        self.dfdict_dump_mavlink = {}


    def load_data(self, cm: ConfigManager) -> None:
        
        for file in natsorted(list(self.sensors_path.iterdir())):
            if file.suffix.lower() == ".log":
                print('\ninfo: Loadind autopilot data :', file)
                self.dfdict_dump_mavlink = parse_raw_log(file, cm.get_parse_keys())
                break
            if file.suffix.lower() == ".bin":
                print('\ninfo: Loadind autopilot data :', file)
                self.dfdict_dump_mavlink = parse_raw_bin(file, cm.get_parse_keys())
                break
        

    def dont_have_log_file(self) -> bool:
        return len(self.dfdict_dump_mavlink) == 0


    def cannot_perform_bathy_post_processing(self) -> bool:
        return len(self.df_bathy) == 0


    def run_bathy_analysis(self, cm: ConfigManager, session_info_path: Path, navigation_file: Path) -> None:
        
        print('\ninfo: Generate waypoints file from bin')
        generate_theoric_waypoints_file(self.sensors_path, self.dfdict_dump_mavlink["CMD"])
    
        print('\ninfo: Write start and end GPStime of the mission in session_info')
        write_real_mission_interval(session_info_path, self.dfdict_dump_mavlink[cm.get_parse_key_gps()], self.dfdict_dump_mavlink["MSG"])

        print('\ninfo: Build base dataframe from GPS')
        self.df_bathy, self.filt_exclude_specific_datetimeUnix = build_dataframe_gps(self.dfdict_dump_mavlink, cm, navigation_file)
        print('info: number of point in main dataframe : ', len(self.df_bathy))

        if len(self.df_bathy) == 0: 
            print("No more points to analyze due to filtering")
            return 

        print('info: GPS log starts >',self.df_bathy.GPS_time.values[0])
        print('info: GPS log ends   >',self.df_bathy.GPS_time.values[-1])

        print('\ninfo: Estimate attitude at GPS positions')
        df_att = self.dfdict_dump_mavlink[cm.get_parse_key_att()]
        self.df_bathy = calc_att_at_gps_coord(self.df_bathy, df_att, cm.get_bathy_max_angle())
        print('info: number of point in main dataframe : ', len(self.df_bathy))
        
        print('\ninfo: Estimate raw depth at GPS positions')
        df_dpth = self.dfdict_dump_mavlink[cm.get_parse_key_depth()]
        self.df_bathy = calc_raw_depth_at_gps_coord(self.df_bathy, df_dpth, cm)
        print('info: number of point in main dataframe : ', len(self.df_bathy))
        
        print('\ninfo: Correct depth values')
        self.df_bathy = calc_ign_depth_at_gps_coord(self.df_bathy, cm)
        print('info: number of point in main dataframe : ', len(self.df_bathy))
        
        if (len(self.df_bathy) == 0): 
            print("No more points to analyze due to filtering")
            return
        
        print('\ninfo: Save to file')
    
        # dump processed data
        self.df_bathy.to_csv(Path(self.bathy_path, 'bathy_preproc.csv'), sep=',', index=False)
        
        # dump associated metadata
        cm.save_cfg_prog(Path(self.bathy_path, 'bathy_preproc.csv.metadata'))
        
        ###### section : plot data #####
        print('\ninfo: Plot data')
        
        plot_basic_bathy_data_time(self.df_bathy, self.bathy_path, 'preproc')
        plot_basic_bathy_data_2D(self.df_bathy, self.bathy_path, 'preproc')
        
        print('\ninfo: Generate interactive map')
        # generate map base layer
        fmap = folium_map_gen_sat_layer_EsriSat()
        # add scatter data (layer name have to be unique)
        fmap = folium_map_add_scatterdata(fmap, self.df_bathy, 'depth')
        # add line data (layer name have to be unique)
        fmap = folium_map_add_linepath(fmap, self.df_bathy, 'track')
        # Add layer control to show/hide data
        folium.LayerControl().add_to(fmap)
        
        print('\ninfo: Save interactive map')
        fmap.save(Path(self.bathy_path, 'webmap_usv_track.html'))
    

    def run_bathy_postprocessing(self, cm: ConfigManager) -> None:

        ###### section : interpolate bathy to regular grid
        # time func execution
        texec = datetime.now()
        
        print('\nRunning open3D modelization...')

        # load initial data to compute average distance before generating gridded data
        print('Computing initial point cloud average distance')
        # get x, y, and z values in a numpy array
        xyz = np.array(self.df_bathy[['X_utm_corr','Y_utm_corr','Depth_corr']])
        # xyz = np.array(df[['Lng_corr','Lat_corr','Depth_corr']])
        # build point cloud from xyz matrix
        pcd, avgdist, stddist = build_o3d_pointcloud(xyz)
        print('stddist >>>>>>',stddist)
        # gen gridded data
        print('Generating gridded data')
        cm.set_mesh_spacing_m(np.round((avgdist+3*stddist),3)) 
        df_grid = gen_gridded_depth_data(self.df_bathy, cm)
        
        # get x, y, and z values in a numpy array
        print('Computing final point cloud and mesh')
        xyz = np.array(df_grid[['X_utm_corr','Y_utm_corr','Depth_corr']])
        # build point cloud from xyz matrix
        pcd, avgdist , _ = build_o3d_pointcloud(xyz)
        # build mesh with faces from point cloud
        mesh = build_o3d_trimesh(pcd,avgdist,method=cm.get_mesh_3dalgo())
        
        print('Done ... open3D mesh computed')
        
        print('\ninfo: Save gridded data to csv file')
        
        # set tags for file names
        tags = '{0}'.format(cm.get_mesh_method())
        
        # dump postprocessed data
        df_grid.to_csv(Path(self.bathy_path, f"bathy_postproc_{tags}.csv"), sep=',', index=False)
        
        # dump associated metadata
        cm.save_cfg_prog(Path(self.bathy_path, f"bathy_postproc_{tags}.csv.metadata"))
        
        # Plot post-processed bathy data
        print('\ninfo: Generate simple plot of post-processed data')
        plot_basic_bathy_data_2D(df_grid, self.bathy_path, 'postproc_'+tags)   
        
        # Shapefile with geopandas
        print('\ninfo: Generating shapefile from gridded data')
        df_shp = df_grid[['Lng_corr','Lat_corr','Depth_corr']]
        df_shp.columns = ['lng','lat','depth']
        df_shp_geometry = df_shp.assign(geometry=df_shp.apply(lambda row: Point(row.lng,row.lat,row.depth),axis=1))

        gdf = gpd.GeoDataFrame(df_shp_geometry, geometry=df_shp_geometry.geometry)
        gdf.set_crs(epsg=4326, inplace=True)
        gdf.to_file(Path(self.bathy_path, f"{cm.get_session_name()}_bathy_shapefile-pointcloud-{tags}.shp"))
        print("Shapefile created")

        # Raster with geocube
        print('\ninfo: Generating raster from gridded data')
        resol_lng = np.median([np.abs(gdf.iloc[i].lng - gdf.iloc[i+1].lng) for i in range(len(gdf)-1)])
        resol_lat = np.median([np.abs(gdf.iloc[i].lat - gdf.iloc[i+1].lat) for i in range(len(gdf)-1)])
        resol = np.min([resol_lng, resol_lat])
        maxnbpt = 1e6
        condpt = ((np.max(gdf.lng.values)-np.min(gdf.lng.values))/resol) * ((np.max(gdf.lat.values)-np.min(gdf.lat.values))/resol)
        reduceTime = 0
        while condpt >= maxnbpt:
            resol = resol*1.1
            condpt = ((np.max(gdf.lng.values)-np.min(gdf.lng.values))/resol) * ((np.max(gdf.lat.values)-np.min(gdf.lat.values))/resol)
            reduceTime += 1
        print(f'reducing raster resolution {reduceTime} times, file too big otherwise ...')
        print('Done adjusting raster resolution ...')
        print('Building geocube object')
        geo_grid = make_geocube(
            vector_data=gdf,
            measurements=['depth'],
            resolution=(-resol, resol),
            rasterize_function=partial(rasterize_points_griddata, filter_nan=True,  method=cm.get_mesh_method()),
        )
        raster_path = str(Path(self.bathy_path, f"{cm.get_session_name()}_bathy_raster-{tags}.tif"))
        print(f'Rasterize it: {raster_path}')
        geo_grid["depth"].rio.to_raster(raster_path)
        print("Raster created")

        # Shapefile with countours
        print('\ninfo: Generating shapefile with contour lines from raster')
        try:
            # shapefile with countour lines polygons from raster
            nb_line = 10
            z_var = 'depth' # name of columns with depth in tiff file
            interval_m = (np.max(gdf[z_var].values)-np.min(gdf[z_var].values))/nb_line
            interval_m = str(interval_m) # in meter, cast to string

            # shapefile with contour as lines
            out_file_path = str(Path(self.bathy_path, f"{cm.get_session_name()}_bathy_shapefile-contourline-{tags}.shp"))
            gdal_cmd = f'gdal_contour -b 1 -a {z_var} -i {interval_m} {raster_path} {out_file_path}'
            print('COUNTOUR LINE gdal cmd:',gdal_cmd)
            subprocess.run(gdal_cmd, shell=True)

            # shapefile with contour as filled polygon
            out_file_path = str(Path(self.bathy_path, f"{cm.get_session_name()}_bathy_shapefile-contourpoly-{tags}.shp"))
            gdal_cmd = f'gdal_contour -b 1 -p -amax {z_var} -i {interval_m} {raster_path} {out_file_path}'
            print('CONTOUR_POLY gdal cmd:',gdal_cmd)
            subprocess.run(gdal_cmd, shell=True)

        except:
            print(traceback.format_exc(), end="\n\n")
            print('\n--- WARNING ---')
            print('Problem occurs when generating shapefile with countours with gdal. Done nothing ...')
        print('Done ...')
        
        # set tags for file names
        tags = '{0}-{1}'.format(cm.get_mesh_method(),
                                cm.get_mesh_3dalgo())

        # Write 3D object to .ply file
        print('\ninfo: Writing current shapes to ply file in :', self.bathy_path)
        ply_file_name = Path(self.bathy_path, f'{cm.get_session_name()}_bathy_3dmodel-{tags}.ply')
        o3d.io.write_triangle_mesh(str(ply_file_name), mesh, write_ascii=True)

        # change , in . in .ply file if it exist
        replace_comma_by_dot(ply_file_name)
        
        # time func execution
        print('func: exec time --> ',datetime.now() - texec)