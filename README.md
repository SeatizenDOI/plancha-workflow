<p align="center">
  <a href="https://github.com/SeatizenDOI/plancha-workflow/graphs/contributors"><img src="https://img.shields.io/github/contributors/SeatizenDOI/plancha-workflow" alt="GitHub contributors"></a>
  <a href="https://github.com/SeatizenDOI/plancha-workflow/network/members"><img src="https://img.shields.io/github/forks/SeatizenDOI/plancha-workflow" alt="GitHub forks"></a>
  <a href="https://github.com/SeatizenDOI/plancha-workflow/issues"><img src="https://img.shields.io/github/issues/SeatizenDOI/plancha-workflow" alt="GitHub issues"></a>
  <a href="https://github.com/SeatizenDOI/plancha-workflow/blob/master/LICENSE"><img src="https://img.shields.io/github/license/SeatizenDOI/plancha-workflow" alt="License"></a>
  <a href="https://github.com/SeatizenDOI/plancha-workflow/pulls"><img src="https://img.shields.io/github/issues-pr/SeatizenDOI/plancha-workflow" alt="GitHub pull requests"></a>
  <a href="https://github.com/SeatizenDOI/plancha-workflow/stargazers"><img src="https://img.shields.io/github/stars/SeatizenDOI/plancha-workflow" alt="GitHub stars"></a>
  <a href="https://github.com/SeatizenDOI/plancha-workflow/watchers"><img src="https://img.shields.io/github/watchers/SeatizenDOI/plancha-workflow" alt="GitHub watchers"></a>
</p>

<div align="center">
  <img src="images/Img50-B4Planche.JPG" alt="Project logo" width="700">
  <p align="center">Process a plancha-session after data collection. Image by Rémi Leroy.</p>
  <a href="https://github.com/SeatizenDOI/plancha-workflow">View framework</a>
  ·
  <a href="https://github.com/SeatizenDOI/plancha-workflow/issues">Report Bug</a>
  ·
  <a href="https://github.com/SeatizenDOI/plancha-workflow/issues">Request Feature</a>
</div>

<div align="center">

# Plancha Workflow

</div>

This repository allows the data retrieved by the [Plancha](https://ocean-indien.ifremer.fr/en/Projects/Technological-innovations/PLANCHA-2021-2023) project to be processed .


## Summary

* [Installation](#installation)
* [Usage](#usage)
* [Workflow](#workflow)
* [Plancha config file](#plancha-config-file)
* [CSV input file](#csv-input-file)
* [Contributing](#contributing)
* [License](#license)


## Installation

To ensure a consistent environment for all users, this project uses a Conda environment defined in a `plancha_env.yml` file. Follow these steps to set up your environment:

1. **Install Conda:** If you do not have Conda installed, download and install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution).

2. **Third-party libraries (with ubuntu example):** 
    * [ExifTool](https://exiftool.org/)
    * [Rtklib](https://rtklibexplorer.wordpress.com/tag/rnx2rtkp/)
    * [Ffmpeg](https://ffmpeg.org/)

    On ubuntu 22.04, you can download all with `sudo apt-get install libimage-exiftool-perl ffmpeg rtklib`

3. **Create the Conda Environment:** Navigate to the root of the project directory and run the following command to create a new environment from the `plancha_env.yml` file:
   ```bash
   conda env create -f plancha_env.yml
   ```

4. **Activate the Environment:** Once the environment is created, activate it using:
   ```bash
   conda activate plancha_env
   ```

## Usage

To run the workflow, navigate to the project root and execute:

```bash
python workflow.py [OPTIONS]
```

Where `[OPTIONS]` can include:

- `csv`: Path to the CSV file for the session name. Default is None.
- `os`, `--only-split`: Only split images from videos.
- `ns`, `--no-split`: Don't split images from videos.
- `na`, `--no_annotate`: Don't annotate images.
- `nb`, `--no_bathy`: Don't process bathymetry.
- `nc`, `--no_clean`: Specify folder to clean (f: FRAMES, m: METADATA, b: BATHY, g: GPS). Example: -no_clean fm. Default is an empty string.
- `frgp`, `--force_use_rgp`: Force the use of RGP station to compute base GPS.
- `rp`, `--root_path`: Root path for the session. Default is None.
- `rf`, `--remove_frames`: Remove frames until the specified number is met. Default is None.
- `pcn`, `--plancha_config_path`: Path to the plancha config file to use. Default is None


## Workflow

The first step is to centralize the raw data:
- Videos or Image (need to have all image at same level) on the gopro
- Connect to the Base, if using an emlid RS2, to retrieve the RINEX and LLH. If you're using data from an RGP station, enter it in the plancha_config.json file.
- Connect to the board's emlid M2 and retrieve RINEX and LLH
- Bin file provided by pixhawk

The next step is to arrange the raw data in a file structure like this one:

```
YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number
├── DCIM : folder to store videos and photos depending on the media collected
├── GPS : folder to store any positioning related file. If any kind of correction is possible on files (e.g. Post-Processed Kinematic thanks to rinex data) then the distinction between device data and base data is made. If, on the other hand, only device position data are present and the files cannot be corrected by post-processing techniques (e.g. gpx files), then the distinction between base and device is not made and the files are placed directly at the root of the GPS folder. 
│   ├── BASE :  files coming from rtk station or any static positioning instrument
│   └── DEVICE : files coming from the device
├── METADATA : folder with general information files about the session
├── PROCESSED_DATA : contain all the folders needed to store the results of the data processing of the current session. 
│   ├── BATHY :  output folder for bathymetry raw data extracted from mission logs
│   ├── FRAMES :  output folder for georeferenced frames extracted from DCIM videos
│   ├── IA :  destination folder for image recognition predictions
│   └── PHOTOGRAMMETRY :  destination folder for reconstructed models in photogrammetry
└── SENSORS : folder to store files coming from other sources (bathymetry data from the echosounder, log file from the autopilot,  mission plan etc.)
```

## Plancha config file

This file contains all the parameters necessary to process a session.

### session_info

| field | effect |
| :-- | :--   |
| session_name | Name of the session following this nomenclature: YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number |
|root   | Folder where the session is stored |
| delete_processed_session | Name of the session following this nomenclature: YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number


### dcim

| field | effect |
| :-- | :--   |
| exiftool_config_path | Relative path to exiftool configuration file. Mandatory to add GPSRoll and GPSPitch in frame metadata |
|  frames_per_second |  Split videos in dcim at this framerate. Can be integer or fraction |
| leap_sec |  See https://en.wikipedia.org/wiki/Leap_second, since 2017 it's 18 secs |
| time_first_frame_UTC |  UTC+0 Time indicate on first frame in the format YYYY:MM:DD HH:MM:SS.000 |
| first_frame_to_keep |  After split videos, session_name_1_{first_frame_to_keep} to match with time_first_frame_UTC. All previous frames are removed |
| remove_frames_outside_mission |  Remove frames outside mission Keep frames unless mission interval isn't found |
| filt_exclude_specific_datetimeUTC | Exclude specific interval for frames with UTC interval |

### gps

| field | effect |
| :-- | :--   |
| ppk_config_path | Folder path to the ppk_config file.|
| ppk_config_name | PPK config file is the config used by rtklib to compute ppk |      
| force_use_rgp | Boolean to force use data from RGP station as base |
| rgp_station |  Name of the rgp station |
| use_llh_position| We have to way to acquire correct gps values. The first one is with RTK(Reak time Kinetics). Device get real time correction during acquisition. We use LLH file. The second one is PPK (Post processed Kinetics). We need to have a motionless base to acquire base position. Which both rinex files of the Base and the device, we compute correct GPS values. If use_llh_position is set to true to use PPK solution else RTK solution. |
| gpsbaseposition_mean_on_llh | Only work with **use_llh_position** set to true. In ppk_config_file, we have three line called ant2-pos(1, 2, 3) is for the position of the base reference. If gpsbaseposition_mean_on_llh is set to true, we compute the mean position of our base to get the best position. If set to false, we use data give by IGN. |
| utm_zone | The UTM zone number for the survey area (Reunion=40) |
| utm_south |    Is UTM zone is in south hemisphere ?|
| utm_ellips |    Reference ellipsoid (typ: WSG84)|
| filt_rtkfix |    From gps data, we have three status point (Q1, Q2, Q5). If filt_rtkfix is set to true, we keep only Q1 value.|
| filt_waypoint | Enable/disable filtering GPS data according to ASV mission progress|
| filt_exclude_specific_timeUS | Exclude bathy data on specific interval|

### parse
| field | effect |
| :-- | :--   |
| gpskey | Keyword for GPS data in autopilot log |
| attkey | Keyword for attitude data in autopilot log |
| dpthkey | Keyword for depth data in autopilot log |
| optkey | Keyword list for other data in autopilot log |

### bathy

| field | effect |
| :-- | :--   |
| offset_ant_beam| Table with X,Y,Z offsets from GPS antenna and to echosounder beam (X facing forward, Y facing left and Z facing upward) | 
| dpth_coef| Scale factor for depth values | 
| max_angle| ASV max angle for pitch and roll values. If greater, points are removed. | 
| dpth_range| Min and max allowed depth values. If outside, points are removed | 
| dpth_win_s| Sliding window duration in second for the depth median filter | 
| dpth_valid_prop| Proportion of inliers inside the sliding window to consider the prediction valid | 
| use_geoid| Enable/Disable depth correction with geoid and GPS altitude | 
| geoid_path| Path to geoid grid if enabled | 

### mesh 

| field | effect |
| :-- | :--   |
| spacing_m| (autofilled) Point spacing in meters for the mesh-grid | 
| method| Depth interpolation method over mesh-grid ("linear", "cubic", "nearest") | 
| 3Dalgo| Algorithm used for surface reconstruction over computed mesh-grid data. ("ballpivot" , "alphashape") | 

## CSV input file

This file is used to process several sessions one after the other.

| field | effect |
| :-- | :--   |
| session_name | Name of the session following this nomenclature: YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number |
| time_first_frame | UTC+0 Time indicate on first frame in the format YYYY:MM:DD HH:MM:SS.000 |
| number_first_frame | After split videos, session_name_1_{first_frame_to_keep} to match with time_first_frame_UTC. All previous frames are removed |
| filt_exclude_specific_timeUS | Exclude bathy data on specific interval |
| depth_range_max | Max allowed depth values |
| depth_range_min | Min allowed depth values |
| filt_exclude_specific_datetimeUTC | Allow to filter frame by utc interval. |
| rgp_station | Name of rgp station. If filled, force to use rgp station instead base. |

## Contributing

Contributions are welcome! To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Commit your changes with clear, descriptive messages.
4. Push your branch and submit a pull request.

## License

This framework is distributed under the wtfpl license. See `LICENSE` for more information.

<div align="center">
  <img src="https://github.com/SeatizenDOI/.github/blob/main/images/logo_partenaire.png?raw=True" alt="Partenaire logo" width="700">
</div>