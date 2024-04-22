import os
import shutil
import traceback
from pathlib import Path

FOLDER_SAVED_GPS = "/home/bioeos/Documents/Bioeos/OUTPUT_DATA/all_pdf"

def main(root_folders):


    folder_to_move_pdf = Path(FOLDER_SAVED_GPS)
    if not Path.exists(folder_to_move_pdf):
        os.mkdir(folder_to_move_pdf)

    session_name_fails, session_number = [], 0
    for root_name in root_folders:
        
        # Get root folder
        root_folder = Path(root_folders[root_name])
        if not Path.exists(root_folder) or not root_folder.is_dir():
            print(f"\n\n[ERROR ROOT FOLDER] Cannot find root folder or root folder isn't a directory for: {root_folder}\n\n")
            continue
        
        for session in sorted(list(root_folder.iterdir())):
            session_number += 1
            session_name = session.name
            if not session.is_dir():
                print(f"\n\n[ERROR] Session {session} isn't a directory")
                continue

            print(f"\n-- \t Starting with {session}")

            try:
                file_to_copy = Path(session, f"000_{session_name}_preview.pdf")

                if not Path.exists(file_to_copy):
                    print(f"PDF file not found for session {session_name}")
                    continue

                shutil.copy(file_to_copy, Path(folder_to_move_pdf, file_to_copy.name))

            except Exception:
                # Print error
                print(traceback.format_exc(), end="\n\n")
                
                # Store sessions name
                session_name_fails.append(session.name)


if __name__ == "__main__":

    root_folders = {
        "202210_plancha_session": "/media/bioeos/F/202210_plancha_session",
        "202301-07_plancha_session": "/media/bioeos/F/202301-07_plancha_session",
        "202305_plancha_session": "/media/bioeos/F/202305_plancha_session",

        # "2015_plancha_session": "/media/bioeos/E/2015_plancha_session",
        "2021_plancha_session": "/media/bioeos/E/2021_plancha_session",
        "202211_plancha_session": "/media/bioeos/E/202211_plancha_session",
        "202309_plancha_session": "/media/bioeos/E/202309_plancha_session",
        "202310_plancha_session": "/media/bioeos/E/202310_plancha_session",

        "202311_plancha_session": "/media/bioeos/D/202311_plancha_session",
        "202312_plancha_session": "/media/bioeos/D/202312_plancha_session"
    }

main(root_folders)