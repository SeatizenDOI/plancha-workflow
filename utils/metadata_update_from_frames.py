import os
import pandas as pd
from pathlib import Path

root_folders = {
    "202210_plancha_session": "/media/bioeos/F/202210_plancha_session",
    "202301-07_plancha_session": "/media/bioeos/F/202301-07_plancha_session",
    "202305_plancha_session": "/media/bioeos/F/202305_plancha_session",

    # "2015_plancha_session": "/media/bioeos/E/2015_plancha_session",
    # "2021_plancha_session": "/media/bioeos/E/2021_plancha_session",
    "202211_plancha_session": "/media/bioeos/E/202211_plancha_session",
    "202309_plancha_session": "/media/bioeos/E/202309_plancha_session",
    "202310_plancha_session": "/media/bioeos/E/202310_plancha_session",

    "202311_plancha_session": "/media/bioeos/D/202311_plancha_session",
    "202312_plancha_session": "/media/bioeos/D/202312_plancha_session"
}
# root_folders = {
#     "202210_plancha_session": "/home/bioeos/Documents/Bioeos/plancha-session"
# }

CSV = "METADATA/metadata.csv"
keep_param_list = ["ApertureValue", "Compression", "Contrast", "CreateDate", "DateCreated", "DateTimeDigitized", "DateTimeOriginal", "DigitalZoomRatio", "ExifImageHeight", "ExifImageWidth", 
                        "ExifToolVersion", "ExifVersion", "ExposureCompensation", "ExposureMode", "ExposureProgram", "FileName", "FileSize", "FileType", "FileTypeExtension", "FNumber", 
                        "FocalLength", "FocalLength35efl", "FocalLengthIn35mmFormat", "FOV", "GPSAltitude", "GPSAltitudeRef", "GPSDateTime", "GPSDate", "GPSTime", "GPSLatitude", "GPSLatitudeRef", "GPSLongitude", 
                        "GPSLongitudeRef", "GPSMapDatum", "GPSPosition", "GPSTimeStamp", "GPSRoll", "GPSPitch", "GPSTrack", "ImageHeight", "ImageWidth", "LightValue", "Make", "MaxApertureValue", 
                        "MaximumShutterAngle", "Megapixels", "MeteringMode", "MIMEType", "Model", "Saturation", "ScaleFactor35efl", "SceneCaptureType", "SceneType", "SensingMethod", "Sharpness", 
                        "ShutterSpeed", "Software", "SubSecDateTimeOriginal", "ThumbnailImage", "ThumbnailLength", "ThumbnailOffset", "WhiteBalance", "XResolution", "YResolution", "Composite:GPSLatitude", "Composite:GPSLongitude",
                        "GPSfix", "GPSsdne", "GPSsde", "GPSsdn"]

# Iter on each folder
for root_folder in root_folders:
    root_folder_path = Path(root_folders[root_folder])
    print(f"\nWork in {root_folder_path}", end="\n\n")


    if not Path.exists(root_folder_path):
        print(f"Folder {root_folder_path} doesn't exist")
        continue

    for session in sorted(list(Path.iterdir(root_folder_path))):
        print(f"Session {session.name}\n")
        metadata_csv = Path(session, CSV)

        frame_path = Path(session, "PROCESSED_DATA", "FRAMES")
        if not Path.exists(frame_path):
            print(f"Frame path doest exist for session {session.name}")
            continue

        if len(list(frame_path.iterdir())) == 0:
            print(f"Session {session.name} doesn't have frames")
            continue

        # Extract metadata from folder
        export_frame_metadata =  "exiftool -n -csv -fileorder filename " + str(frame_path) + " > temp.csv"
        os.system(export_frame_metadata)

        csv_exiftool_frames = pd.read_csv("temp.csv")

        # intersection between metadata we want to keep and EXIF metadata
        intersection_list = []
        for col in csv_exiftool_frames:
            col = col.split(':')[1] if ':' in col else col
            if col in keep_param_list and col not in intersection_list:
                intersection_list.append(col)

        # filter df
        csv_exiftool_frames = csv_exiftool_frames[intersection_list]
        # delete all empty columns
        csv_exiftool_frames.dropna(axis=1,inplace=True)
        # delete all zero columns
        csv_exiftool_frames = csv_exiftool_frames.loc[:, (csv_exiftool_frames != 0).any(axis=0)]
        # sort metadata columns by name
        csv_exiftool_frames = csv_exiftool_frames.sort_index(axis=1)
        # save filtered frame csv, after import metadata
        csv_exiftool_frames.to_csv(metadata_csv, index=False)



        