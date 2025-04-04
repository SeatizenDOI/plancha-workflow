import os
import datetime
import subprocess
import pandas as pd
import argparse

'''
    From a folder with bin files, display first date in GPS status for each file.
'''

def parse_option():
    parser = argparse.ArgumentParser(prog="verify-bin", description="From a folder with bin files, display first date in GPS status for each file.")
    parser.add_argument("-p", "--path-directory", help="Folder path to bin files", required=True)
    return parser.parse_args()

def main(opt):
    # Get folder path.
    path_directory = opt.path_directory
    if not os.path.exists(path_directory):
        print("Folder not found.")
        return

    # File buffer for csv.
    filebuf = './tmp.csv'
    for file in sorted(list(os.listdir(path_directory))):
        if file.endswith(".BIN"):
            file_path = os.path.join(path_directory, file)

            # Parse bin.
            tmp_cmd = "python ../src/lib/mavlogdump.py --planner --format csv --type GPS "+file_path+" > "+filebuf
            subprocess.call(tmp_cmd, shell=True)

            # Read csv and remove file buffer.
            df = pd.read_csv(filebuf, sep=";")
            os.remove(filebuf)

            # Parse timestamp.
            value = datetime.datetime.fromtimestamp(df.timestamp[0])

            # File size.
            file_size = round(os.path.getsize(file_path) / 1000000, 1)

            print("File {}, time: {}, size: {} Mo ".format(file, value.strftime('%Y-%m-%d %H:%M:%S'), file_size))

if __name__ == "__main__":
    opt = parse_option()
    main(opt)
