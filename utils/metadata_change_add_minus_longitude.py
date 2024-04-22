import pandas as pd
from pathlib import Path

root_folders = {
    "202210_plancha_session": "/media/bioeos/F/202210_plancha_session",
    "202211_plancha_session": "/media/bioeos/E/202211_plancha_session",
    "202301-07_plancha_session": "/media/bioeos/E/202301-07_plancha_session",
    "202309_plancha_session": "/media/bioeos/E/202309_plancha_session",
    "202310_plancha_session": "/media/bioeos/E/202310_plancha_session",
    "202311_plancha_session": "/media/bioeos/D/202311_plancha_session",
    "202312_plancha_session": "/media/bioeos/D/202312_plancha_session"
}
CSV = "METADATA/metadata.csv"

# Iter on each folder
a = 0
for root_folder in root_folders:
    root_folder_path = Path(root_folders[root_folder])
    print(f"\nWork in {root_folder_path}", end="\n\n")


    if not Path.exists(root_folder_path):
        print(f"Folder {root_folder_path} doesn't exist")
        continue

    for session in Path.iterdir(root_folder_path):
        metadata_csv = Path(session, CSV)
        print(f"Session {metadata_csv}: ", end=" ")


        if not Path.exists(metadata_csv):
            print("Not found")
            continue
        
        if Path(metadata_csv).stat().st_size == 0:
            print("CSV File is empty")
            continue

        df = pd.read_csv(metadata_csv)

        if "GPSLatitudeRef" not in list(df) or "GPSLongitudeRef" not in list(df) or "GPSLatitude" not in list(df) or "GPSLongitude" not in list(df):
            print("Header not found")
            continue

        if len(df["GPSLatitudeRef"].unique()) != 1 or len(df["GPSLongitudeRef"].unique()) != 1:
            print("Multiple GPS orientation in one column please verify")
            continue
        
        if "FilePermissions" in list(df):
            print("Metadata file is in an older version")
            continue

        lon, lat = df["GPSLongitudeRef"].unique()[0], df["GPSLatitudeRef"].unique()[0]

        if (lat == 'S' or lat == "South") and df["GPSLatitude"].sum() > 0: # If GPS is South coordinate need to be negative
            df["GPSLatitude"] *= -1.0
        
        if (lon == 'W' or lon == "West") and df["GPSLongitude"].sum() > 0: # If GPS is West coordinate need to be negative
            df["GPSLongitude"] *= -1.0

        # df.to_csv(metadata_csv, index=False)
        print("OK")

