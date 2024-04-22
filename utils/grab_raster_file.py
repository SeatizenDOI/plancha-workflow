from pathlib import Path
import pandas as pd
import os
import shutil

root_folders = {
    "202210_plancha_session": "/media/bioeos/F/202210_plancha_session",
    "202301-07_plancha_session": "/media/bioeos/F/202301-07_plancha_session",
    "202305_plancha_session": "/media/bioeos/F/202305_plancha_session",

    "2015_plancha_session": "/media/bioeos/E/2015_plancha_session",
    "2021_plancha_session": "/media/bioeos/E/2021_plancha_session",
    "202211_plancha_session": "/media/bioeos/E/202211_plancha_session",
    "202309_plancha_session": "/media/bioeos/E/202309_plancha_session",
    "202310_plancha_session": "/media/bioeos/E/202310_plancha_session",

    "202311_plancha_session": "/media/bioeos/D/202311_plancha_session",
    "202312_plancha_session": "/media/bioeos/D/202312_plancha_session"
}

CSV_FILE = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/all_raster/suivi_campagne.csv"
FOLDER_SAVED_RASTER = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/all_raster"

def main():
    csv_file_path = Path(CSV_FILE)
    if not Path.exists(csv_file_path):
        print("Le fichier csv n'existe pas.")
        return

    df = pd.read_csv(csv_file_path)
    df1 = df[df["Victor_approb_complete"] == "v3"] # Keep only v1 and v3 value
    df2 = df[df["Victor_approb_complete"] == "v1"] # Keep only v1 and v3 value
    df3 = df[df["Victor_approb_complete"] == "v2"] # Keep only v1 and v3 value
    df4 = df[df["Victor_approb_complete"] == "v0"] # Keep only v1 and v3 value
    df = pd.concat([df1, df2, df3, df4], ignore_index=True)

    for index, row in df.loc[:, ['session name', 'Stockage']].iterrows():
        session_name = row["session name"]
        stockage = row["Stockage"]

        if stockage not in root_folders:
            print(f"Stockage not found for {session_name}")
            continue
        if len(session_name.split("_")) != 4 and len(session_name.split("_")) != 3:
            print(f"Session not split in 4 or 3 pieces for {session_name}")
            continue
        
        place = session_name.split("_")[1]
        opt_place = "".join(place.split("-")[1:])

        folder_to_move_raster = Path(FOLDER_SAVED_RASTER, opt_place)
        if not Path.exists(folder_to_move_raster):
            os.mkdir(folder_to_move_raster)
        
        bathy_path = Path(root_folders[stockage], session_name, "PROCESSED_DATA/BATHY")
        if not Path.exists(bathy_path):
            print(f"Bathy path doesn't exist {bathy_path}")
            continue

        haveTif = False
        for file in os.listdir(bathy_path):
            if file.endswith(".tif"):
                raster_path = Path(bathy_path, file)
                shutil.copy(raster_path, folder_to_move_raster)
                haveTif = True
                break
        if not haveTif:
            print(f"Session {session_name} doesn't have tif file")

main()

