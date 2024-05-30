import shutil
import argparse
import traceback
import pandas as pd
from pathlib import Path
from tools.parse_tools import get_list_sessions

JACQUES_VERSION = "20240513_v20.0"
MULTILABEL_VERSION = "lombardata_DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze"

def grab_bathy_raster(session_path, output_folder, opt_place):
    folder_to_move_raster = Path(output_folder, opt_place)
    folder_to_move_raster.mkdir(exist_ok=True, parents=True)
    
    bathy_path = Path(session_path, "PROCESSED_DATA/BATHY")
    if not Path.exists(bathy_path):
        print(f"Bathy path doesn't exist {bathy_path}")
        return

    haveTif = False
    for file in bathy_path.iterdir():
        if file.suffix.lower() == ".tif":
            shutil.copy(file, folder_to_move_raster)
            haveTif = True
            break
    
    if not haveTif:
        print(f"Session {session_path.name} doesn't have tif file")

def grab_pdf(session_path, output_folder):
    file_to_copy = Path(session_path, f"000_{session_path.name}_preview.pdf")

    if not Path.exists(file_to_copy):
        print(f"PDF file not found for session {session_path.name}")
        return

    output_folder.mkdir(exist_ok=True, parents=True)
    shutil.copy(file_to_copy, Path(output_folder, file_to_copy.name))

def grab_jacques_predictions(session_path, output_folder, opt_place):

    folder_to_move = Path(output_folder, opt_place)
    folder_to_move.mkdir(exist_ok=True, parents=True)
    ia_path = Path(session_path, "PROCESSED_DATA", "IA")
    if not Path.exists(ia_path) or not ia_path.is_dir():
        print(f"No Processed_data/IA folder found for {session_path}")
        return

    have_file = False
    for file in ia_path.iterdir():
        if file.suffix.lower() == ".csv" and JACQUES_VERSION in file.name and "jacques" in file.name:
            have_file = True
            shutil.copy(file, Path(folder_to_move, file.name))

    if not have_file:
        print(f"Jacques predictions not found for {session_path}")


def grab_ml_predictions(session_path, output_folder, opt_place, isScore=False):
    folder_to_move = Path(output_folder, opt_place)
    folder_to_move.mkdir(exist_ok=True, parents=True)
    ia_path = Path(session_path, "PROCESSED_DATA", "IA")
    if not Path.exists(ia_path) or not ia_path.is_dir():
        print(f"No Processed_data/IA folder found for {session_path}")
        return

    have_file = False
    for file in ia_path.iterdir():
        if file.suffix.lower() == ".csv" and MULTILABEL_VERSION in file.name:
            if not isScore and "scores" not in file.name:
                have_file = True
                shutil.copy(file, Path(folder_to_move, file.name))
            elif isScore and "scores" in file.name:
                have_file = True
                shutil.copy(file, Path(folder_to_move, file.name))
            

    if not have_file:
        print(f"ML predictions/scores not found for {session_path}")
    
def grab_metadata(session_path, output_folder, opt_place, file_to_find):
    folder_to_move = Path(output_folder, opt_place)
    folder_to_move.mkdir(exist_ok=True, parents=True)
    pred_path = Path(session_path, "METADATA", file_to_find)
    if not Path.exists(pred_path):
        print(f"No {file_to_find} file found for {session_path}")
        return

    newpath = Path(folder_to_move, f"{session_path.name}_{pred_path.name}")
    shutil.copy(pred_path, newpath)


def build_jacques_gps(session_path):
    jacques_pred = Path(session_path, "PROCESSED_DATA/IA", f"{session_path.name}_jacques-v0.1.0_model-{JACQUES_VERSION}.csv")
    metadata_path = Path(session_path, "METADATA", "metadata.csv")
    output_file = Path(session_path, "METADATA", "jacques_gps.csv")

    if not Path.exists(jacques_pred) or not Path.exists(metadata_path):
        print(f"File not found to concat jacques pred for {session_path.name}")
        return

    annot_df = pd.read_csv(jacques_pred)
    gps_df = pd.read_csv(metadata_path)
    
    if len(annot_df) == 0 or len(gps_df) == 0:
        print(f"No data in metadata.csv or in jacques.csv")
        return

    # Extract image names from the file paths
    annot_df['Image_name'] = annot_df['FileName']
    gps_df['Image_name'] = gps_df['FileName']

    # Merge the DataFrames based on the image names
    # Sometimes we don't have this information due to no bin
    keys = [key for key in ['Image_name', 'GPSDateTime', 'SubSecDateTimeOriginal', 'GPSLatitude', 'GPSLongitude', 'GPSTrack', 'GPSRoll', 'GPSPitch', 'GPSAltitude'] if key in gps_df] 
    try:
        merged_df = annot_df.merge(gps_df[keys], on='Image_name', how='left')
    except KeyError:
        print("[ERROR] No key to merge gps information in metadata.")
    
    # Drop the 'Image_name' column from merged_df
    merged_df.drop(columns='Image_name', inplace=True)
    merged_df.to_csv(output_file, index=False, header=True)
    
    return output_file 


def remove_jacques_gps(j_gps):
    if j_gps == None: return
    
    j_gps = Path(j_gps)
    if Path.exists(j_gps) and j_gps.is_file():
        j_gps.unlink()


def grab_predictions_raster(session_path, output_folder, opt_place):
        
    ia_path = Path(session_path, "PROCESSED_DATA/IA")
    if not Path.exists(ia_path):
        print(f"IA path doesn't exist {ia_path}")
        return

    for file in ia_path.iterdir():
        if file.suffix.lower() == ".tif":
            class_name = file.name.replace(session_path.name+"_", "").split("_raster")[0].upper()
            folder_to_move_raster = Path(output_folder, class_name)
            folder_to_move_raster.mkdir(exist_ok=True, parents=True)

            shutil.copy(file, folder_to_move_raster)

def csv_merger(folder_to_merge, out_name):
    
    for folder_opt in Path(folder_to_merge).iterdir():
        df_glob = []
        output_name = Path(folder_opt, f"global_{folder_opt.name}_{out_name}.csv")
        for file in folder_opt.iterdir():
            if file.suffix.lower() == ".csv" and "global" not in file.name:
                df = pd.read_csv(file)
                df_glob.append(df)
        if len(df_glob) == 0:
            continue
        a = pd.concat(df_glob, ignore_index=True)
        a.to_csv(output_name, index=False)

def delete_empty_folder(output_folder):

    # Iter on each type folder create with arguments
    for type_folder in Path(output_folder).iterdir():

        # We can have two type of folder : folder with only file like pdf or raster or folder with subfolder name by opt place
        for fileOrFolder in type_folder.iterdir():
            if fileOrFolder.is_file(): continue
            
            if len(list(fileOrFolder.iterdir())) == 0:
                fileOrFolder.rmdir()

    # Iter on each type folder
    for type_folder in Path(output_folder).iterdir():
        if len(list(type_folder.iterdir())) == 0:
            type_folder.rmdir()



def parse_args():
    parser = argparse.ArgumentParser(prog="grab-master", description="Script to grab what you want from a session")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-efol", "--enable_folder", action="store_true", help="Work from a folder of session")
    arg_input.add_argument("-eses", "--enable_session", action="store_true", help="Work with one session")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")

    # Path of input.
    parser.add_argument("-pfol", "--path_folder", default="/home/bioeos/Documents/Bioeos/plancha-session", help="Folder of session")
    parser.add_argument("-pses", "--path_session", default="/home/bioeos/Documents/Bioeos/plancha-session/20231204_REU-TROUDEAU_ASV-2_01", help="One session")
    parser.add_argument("-pcsv", "--path_csv_file", default="/home/bioeos/Documents/project_hub/plancha-inference/csv_inputs/aldabra.csv", help="Session from csv file")

    # Path output csv
    parser.add_argument("-po", "--path_output", default="/home/bioeos/Documents/Bioeos/OUTPUT_DATA/clean_aldabra", help="Output folder to store all your data")

    # What we want to grab.
    parser.add_argument("-jp", "--jacques_prediction", action="store_true", help="Grab all jacques predictions")
    parser.add_argument("-mlp", "--multilabel_predictions", action="store_true", help="Grab all multilabel predictions")
    parser.add_argument("-mls", "--multilabel_scores", action="store_true", help="Grab all multilabel scores")
    parser.add_argument("-mlpgps", "--ml_predictions_gps", action="store_true", help="Grab all multilabel predictions with gps")
    parser.add_argument("-mlsgps", "--ml_scores_gps", action="store_true",help="Grab all multilabel scores with gps")
    parser.add_argument("-jgps", "--jacques_predictions_gps", action="store_true", help="Grab all jacques predictions with gps. But if file not found try to create it")
    parser.add_argument("-pdf", "--pdf", action="store_true", help="Grab all pdf")
    parser.add_argument("-br", "--bathy_raster", action="store_true", help="Grab all bathy raster")
    parser.add_argument("-m", "--metadata", action="store_true", help="Grab all metadata file")
    parser.add_argument("-pr", "--predictions_raster", action="store_true", help="Grab all predictions raster and store by class name")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")
    parser.add_argument("-mcsv", "--merge_csv_file", action="store_true", help="Merge csv file by zone for ml_predictions_gps, ml_scores_gps, jacques_predictions_gps")

    return parser.parse_args()


def main(opt):

    # Create output path
    output_folder = Path(opt.path_output)
    output_folder.mkdir(exist_ok=True, parents=True)

    bathy_output = Path(output_folder, "BATHY_RASTER")
    pdf_output = Path(output_folder, "PDF")
    jp_output = Path(output_folder, "JACQUES")
    mlpred_output = Path(output_folder, "ML_PRED")
    mlscores_output = Path(output_folder, "ML_SCORES")
    mlpredgps_output = Path(output_folder, "ML_PRED_GPS")
    mlscoregps_output = Path(output_folder, "ML_SCORES_GPS")
    jpgps_output = Path(output_folder, "JACQUES_PRED_GPS")
    metadata_output = Path(output_folder, "METADATA")
    predictions_output = Path(output_folder, "PREDICTIONS_RASTER")

    # Stat
    sessions_fail = []
    list_session = get_list_sessions(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_session) else 0

    for session_path in list_session[index_start:]:
        try:
            print(f"\n-- Working with session {session_path}")
            
            # Check and parse session name
            if not Path.exists(session_path) or not session_path.is_dir():
                print(f"\n\n[ERROR] Session {session_path} isn't a directory")
                continue

            if len(session_path.name.split("_")) != 4:
                print(f"Session not split in 4 pieces for {session_path.name}")
                continue
            
            date, place, asv, session_number = session_path.name.split("_")
            alpha3, opt_place = place.split("-")[0], place.split("-")[-1]
            
            if opt.bathy_raster:
                grab_bathy_raster(session_path, bathy_output, opt_place)
            
            if opt.pdf:
                grab_pdf(session_path, pdf_output)
            
            if opt.jacques_prediction:
                grab_jacques_predictions(session_path, jp_output, opt_place)
            
            if opt.multilabel_predictions:
                grab_ml_predictions(session_path, mlpred_output, opt_place)
            
            if opt.multilabel_scores:
                grab_ml_predictions(session_path, mlscores_output, opt_place, isScore=True)
            
            if opt.ml_predictions_gps:
                grab_metadata(session_path, mlpredgps_output, opt_place, "predictions_gps.csv")
            
            if opt.ml_scores_gps:
                grab_metadata(session_path, mlscoregps_output, opt_place, "predictions_scores_gps.csv")
            
            if opt.jacques_predictions_gps:
                j_gps_file = build_jacques_gps(session_path)
                grab_metadata(session_path, jpgps_output, opt_place, "jacques_gps.csv")
                remove_jacques_gps(j_gps_file)

            if opt.metadata:
                grab_metadata(session_path, metadata_output, opt_place, "metadata.csv")

            if opt.predictions_raster:
                grab_predictions_raster(session_path, predictions_output, opt_place)

        except Exception:
            print(traceback.format_exc(), end="\n\n")
            sessions_fail.append(session_path.name)
    
    print("\n\n-- Done to grab all file")
    if opt.merge_csv_file:
        print("\n\n-- Merging all csv gps file")
        
        if opt.ml_predictions_gps : csv_merger(mlpredgps_output, "ml_predictions_gps") 
        if opt.ml_scores_gps : csv_merger(mlscoregps_output, "ml_scores_gps") 
        if opt.jacques_predictions_gps : csv_merger(jpgps_output, "jacques_gps") 
        if opt.metadata : csv_merger(metadata_output, "metadata")

    print("\n\n Delete empty folder")
    delete_empty_folder(output_folder)

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_session), len(sessions_fail)))
    if (len(sessions_fail)):
        [print("\t* " + session_name) for session_name in sessions_fail]

if __name__ == "__main__":
    opt = parse_args()
    main(opt)