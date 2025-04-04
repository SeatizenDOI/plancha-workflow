import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FormatStrFormatter

from ..enum.StandardDeviationType import StandardDeviationType, get_title_based_on_sd_type

def plot_gps_quality(gps_device_path: Path, csv_llh: pd.DataFrame, session_info: pd.DataFrame, file_name: str) -> None:
    figname = Path(gps_device_path, file_name)

    for file in gps_device_path.iterdir() :
        if file.name == figname:
            print(f"We already have the following figure : {figname}")
            return  
    fig, ax = plt.subplots()
    lat1 = csv_llh.GPSLatitude
    lon1 = csv_llh.GPSLongitude
    gps_val = csv_llh.fix
    
    # Function to map the gps quality signal to standard rtklib colors
    def pltcolor(lst):
        cols = []
        for l in lst:
            if l == 1:
                cols.append('green')
            elif l == 2:
                cols.append('yellow')
            else:
                cols.append('red')
        return cols
    
    cols=pltcolor(gps_val)
    plt.scatter(lat1, lon1, s=5, c=cols)
    # prevent scientific notation 
    ax.ticklabel_format(useOffset=False)
    # specify format of floats for tick labels
    ax.xaxis.set_major_formatter(FormatStrFormatter('%.4f'))
    # less labels on x axis
    plt.locator_params(nbins=8)
    # define graph labels
    plt.xlabel("Lng")
    plt.ylabel("Lat")
    plt.title(' '.join(file_name.split('.')[0].split('_'))) # Get title from file name. EX: GPS_position_accuracy.png => GPS position accuracy
    # add color patch for legend
    green_patch = mpatches.Patch(color='green', label='Q1 = %.3f' %session_info["Q1 ppk Percentage"].iloc[0])
    yellow_patch = mpatches.Patch(color='yellow', label='Q2 = %.3f' %session_info["Q2 ppk Percentage"].iloc[0])
    red_patch = mpatches.Patch(color='red', label='Q5 = %.3f' %session_info["Q5 ppk Percentage"].iloc[0])
    plt.legend(handles=[green_patch, yellow_patch, red_patch])
    print('\nSaving ', file_name, ' image in path\n', gps_device_path)
    plt.savefig(figname,dpi=600)  
    plt.clf()


def plot_standard_deviation(gps_device_path: Path, csv_llh: pd.DataFrame, file_name: str, sd_type: StandardDeviationType) -> None:
    
    figname = Path(gps_device_path, file_name)

    for file in gps_device_path.iterdir() :
        if file.name == figname:
            print(f"We already have the following figure : {figname}")
            return    

    sd_title = get_title_based_on_sd_type(sd_type)
    sd_value = sd_type.value
 
    plt.hist(x=csv_llh[sd_value], range=(0,5), bins=100, color='#0504aa',
                                alpha=0.7)
    plt.grid(axis='y', alpha=0.75)
    plt.xlabel('Meters')
    plt.ylabel('Frequency')
    title = f"{sd_title} distribution,  μ = {np.mean(csv_llh[sd_value])} σ = {np.std(csv_llh[sd_value])}"
    plt.title(title)
    print(f'\nSaving {file_name} image in path\n {gps_device_path}')
    plt.savefig(figname,dpi=600)
    plt.clf()