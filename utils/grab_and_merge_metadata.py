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

PLACE = "TROUDEAU"
PATH_TO_MERGE = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/"
FILE_NAME = "all_metadata_troudeau.csv"
def main():
    all_df = []
    for root_name in root_folders:
            
        # Get root folder
        root_folder = Path(root_folders[root_name])
        if not Path.exists(root_folder) or not root_folder.is_dir():
            print(f"\n\n[ERROR ROOT FOLDER] Cannot find root folder or root folder isn't a directory for: {root_folder}\n\n")
            continue
        
        for session_path in sorted(list(root_folder.iterdir())):
            session = Path(session_path)
            session_name = session.name

            if not session_path.is_dir():
                print(f"\n\n[ERROR] Session {session_path} isn't a directory")
                continue

            if len(session_name.split("_")) != 4 and len(session_name.split("_")) != 3:
                print(f"Session not split in 4 or 3 pieces for {session_name}")
                continue

            place = session_name.split("_")[1]
            opt_place = "".join(place.split("-")[1:])

            if opt_place != PLACE:
                continue

            csv_session = Path(session, "METADATA", "metadata.csv")
            if not Path.exists(csv_session):
                print(f"CSV metadata doesn't exist for session {session_name}")
                continue

            df_session = pd.read_csv(csv_session)
            all_df.append(df_session)
            
    df_final = pd.concat(all_df, ignore_index=True)
    df_final.to_csv(Path(PATH_TO_MERGE, FILE_NAME), index=False)

main()