import folium
import numpy as np
import pandas as pd
import branca.colormap as cm

def folium_map_gen_sat_layer_EsriSat() -> folium.Map:
    fmap = folium.Map(max_zoom=25)
    tile = folium.TileLayer(
            tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr = 'Esri',
            name = 'Esri Satellite',
            overlay = False,
            control = True
           ).add_to(fmap)
    return fmap


def folium_map_add_linepath(fmap: folium.Map, df: pd.DataFrame, layername: str) -> folium.Map:
    group = folium.map.FeatureGroup(name=layername)
    # convert lat lon data to nparray
    points = np.array([df.Lat_corr, df.Lng_corr]).T
    # create line and add to map
    poly = folium.PolyLine(locations=points,
                    color="red", weight=1, opacity=1,
                    ).add_to(group)
    fmap.add_child(group)
    # Set the zoom to the maximum possible
    fmap.fit_bounds(group.get_bounds())
    return fmap


def folium_map_add_scatterdata(fmap: folium.Map, df: pd.DataFrame, layername: str) -> folium.Map:
    group = folium.map.FeatureGroup(name=layername)
    # clean 'nan' values in gridded data
    dbuf = df.copy()
    dbuf = dbuf[np.invert(np.isnan(dbuf.Depth_corr))]
    # build the colormap with depth limits
    cmap = cm.linear.viridis.scale(np.min(df.Depth_corr),np.max(df.Depth_corr))
    # Parse each df rows and draw a circle at each location, color=depth
    for ind, row in dbuf.iterrows():
        c=folium.Circle(location=[row.Lat_corr, row.Lng_corr],
                        fill=True,
                        color=cmap(row.Depth_corr),
                        popup=folium.Popup(html="Time Us: {} <br> gpstime: {}".format(row.TimeUS, row.GPS_time)), 
                        radius=0.001,
                        ).add_to(group)
    fmap.add_child(group)
    #Set the zoom to the maximum possible
    fmap.fit_bounds(group.get_bounds())
    return fmap


def folium_map_combine_data_to_single_map(df_list,outdir,figname='bathymap',combine_mission=False,):
    print('\ninfo: Plot interactive map')

    # generate map base layer
    fmap = folium_map_gen_sat_layer_EsriSat()

    if combine_mission == True:
        df_combi = pd.concat(df_list)
        # add scatter and line data (layer name have to be unique)
        fmap = folium_map_add_scatterdata(fmap,df_combi,'depth')
        fmap = folium_map_add_linepath(fmap,df_combi,'track')
    else:
        # loop for gridded data
        layind = 0
        for data in df_list:
            # add scatter data (layer name have to be unique)
            fmap = folium_map_add_scatterdata(fmap,data,'depth'+str(layind))
            layind = layind + 1
        # loop for corrected data (ASV track)
        layind = 0
        for data in df_list:
            # add line data (layer name have to be unique)
            fmap = folium_map_add_linepath(fmap,data,'track'+str(layind))
            layind = layind + 1

    # Add layer control to show/hide data
    folium.LayerControl().add_to(fmap)

    print('\ninfo: Save interactive map')

    filepath = outdir
    fmap.save(filepath+figname+'.html')

    return fmap