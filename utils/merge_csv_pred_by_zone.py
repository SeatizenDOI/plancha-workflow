import argparse
import pandas as pd
from pathlib import Path


PATH_TO_MERGE = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/stleu_matteo/"
IA_NAME = "lombardata_DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze"
ROOT_FOLDERS = {
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

def parse_option():
    parser = argparse.ArgumentParser(prog="merge_csv_pred_by_zone", description="Merge all csv pred by zone.")
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-eroot", "--enable_root", action="store_true", help="Take all sessions from root folders")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Take all sessions in csv file")

    parser.add_argument("-pcsv", "--path-csv", default="../../hugging-sunnith/csv_inputs/troudeau.csv", help="Path to csv file")

    return parser.parse_args()


def update(list_sessions):

    for session_path in list_sessions:
        session = Path(session_path)
        session_name = session.name

        if not session.is_dir():
            print(f"\n\n[ERROR] Session {session_path} isn't a directory")
            continue

        if len(session_name.split("_")) != 4 and len(session_name.split("_")) != 3:
            print(f"Session not split in 4 or 3 pieces for {session_name}")
            continue

        csv_session = Path(session, "METADATA", "metadata_scores_gps.csv")
        if not Path.exists(csv_session):
            print(f"CSV predictions doesn't exist for session {session_name}")
            continue

        df_session = pd.read_csv(csv_session)
        
        place = session_name.split("_")[1]
        opt_place = "".join(place.split("-")[1:])

        csv_name_to_write = Path(PATH_TO_MERGE, f"prediction_scores_{opt_place}_{IA_NAME}.csv")
        if Path.exists(csv_name_to_write):
            df2 = pd.read_csv(csv_name_to_write)
            df_session = pd.concat([df_session, df2], ignore_index=True)
        
        df_session.to_csv(csv_name_to_write, index=False)

def main(opt):

    if opt.enable_root:
        for root_name in ROOT_FOLDERS:
            # Get root folder
            root_folder = Path(ROOT_FOLDERS[root_name])
            if not Path.exists(root_folder) or not root_folder.is_dir():
                print(f"\n\n[ERROR ROOT FOLDER] Cannot find root folder or root folder isn't a directory for: {root_folder}\n\n")
                continue

            update(sorted(list(root_folder.iterdir())))
    else:
        csv_path = Path(opt.path_csv)
        if Path.exists(csv_path):
            df = pd.read_csv(csv_path)
            list_session = [str(Path(row.root_folder, row.session_name)) for row in df.itertuples(index=False)]
            update(list_session)

if __name__ == "__main__":
    opt = parse_option()
    main(opt)