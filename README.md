<div align="center">

# plancha-workflow

</div>

Ce dépôt permet de traiter les données récupérées par le projet [Plancha](https://ocean-indien.ifremer.fr/en/Projects/Technological-innovations/PLANCHA-2021-2023).
Il découpe les vidéos en images et les géoréférence après avoir recalibré les positions GPS. 

# Summary

* [Installation](#installation)
* [Plancha config file](#plancha-config-file)



## Installation

## Linux user (test on Ubuntu 22.04)

### Conda env

At root folder :
```bash
conda create --name plancha_env --file conda_env/linux_plancha_env.yml
conda activate plancha_env
```

### CRX2RNX

https://terras.gsi.go.jp/ja/crx2rnx.html


### Tecq

[Documentation link](https://www.unavco.org/software/data-processing/teqc/teqc.html)
```bash
cd /home/$USER/Téléchargements
wget https://www.unavco.org/software/data-processing/teqc/development/teqc_CentOSLx86_64s.zip && unzip teqc_CentOSLx86_64s.zip
sudo mv teqc /bin
cd && teqc -version
```

Output:
```bash
executable:  teqc
version:     teqc  2019Feb25
build:       Linux 2.6.32-573.12.1.x86_64|x86_64|gcc -static|Linux 64|=+
```

### ExifTool

[Documentation link](https://exiftool.org/)
```bash
sudo apt install libimage-exiftool-perl
```

### rtklib

[Documentation link](https://rtklibexplorer.wordpress.com/tag/rnx2rtkp/)

Ubuntu : 
```bash
sudo apt install rtklib
```

Windows : 

## Plancha config file <!--TODO finish-->

Configuration file has multiples options for gps :

- **ppk_config_path** <br/>
Folder path to the file.

- **ppk_config_name** <br/>
Name of the file.

- **use_llh_position** <br/>
We have to way to acquire correct gps values. The first one is with RTK(Reak time Kinetics). Device get real time correction during acquisition. We use LLH file. The second one is PPK (Post processed Kinetics). We need to have a motionless base to acquire base position.
Which both rinex files of the Base and the device, we compute correct GPS values.
If use_llh_position is set to true to use PPK solution else RTK solution.

- **gpsbaseposition_mean_on_llh** <br/>
Only work with **use_llh_position** set to true.
In ppk_config_file, we have three line called ant2-pos(1, 2, 3) is for the position of the base reference. If gpsbaseposition_mean_on_llh is set to true, we compute the mean position of our base to get the best position. If set to false, we use data give by IGN.

- **filt_rtkfix** <br/>
From gps data, we have three status point (Q1, Q2, Q5). If filt_rtkfix is set to true, we keep only Q1 value.

- **filt_automode** <br/>
If set to true, we keep only auto value and not manual value.

- **filt_waypoint** <br/>
If set to true, we keep value between WP1 and last WP. We didn't keep data on the beach.


## CHEATSHEET

Only split videos in csv
```bash
    python workflow.py -csv -os
```

Process gps, bathy and annotations from csv with existing frames
```bash
    python workflow.py -csv -no_split -nc f
```


Only run bathy and gps from csv
```bash
    python workflow.py -csv -no_split -nc f -na
```

## CSV FILE

Actually we have five header:
- session_name
- time_first_frame_utc
- image number to be the first frame
- filt_exclude_specific_timeUS
- Bathy max depth

# References

- https://stackoverflow.com/questions/44005694/no-module-named-gdal

## Ubuntu installation 22.04

```bash
conda create --name plancha_clean_env python=3.9
conda activate plancha_clean_env

pip install geocube ffmpeg-python open3d hatanaka wget PyExifTool transforms3d folium pymavlink pycountry pytz
```