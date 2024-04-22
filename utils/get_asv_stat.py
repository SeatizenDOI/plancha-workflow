import os
import argparse
import subprocess
import pandas as pd
from pathlib import Path

'''
    From a folder with bin files, display first date in GPS status for each file.
'''

def parse_option():
    parser = argparse.ArgumentParser(prog="asv-stat", description="From a folder with bin files, display first date in GPS status for each file.")
    parser.add_argument("-p", "--path-directory", help="Folder path to bin files", required=True)
    return parser.parse_args()

def seconds_to_hoursminsec(amount):
    amount = int(amount)
    hours = str(amount // 3600).rjust(2, '0')
    mins = str((amount % 3600) // 60).rjust(2, '0')
    return f"{hours}h{mins}min"

def main(opt):
    # Get folder path.
    path_dir = Path(opt.path_directory)
    if not Path.exists(path_dir):
        print("File not found.")
        return

    # File buffer for csv.
    filebuf = './tmp.csv'
    for file in sorted(list(path_dir.iterdir())):
        if file.suffix.upper() != ".BIN": continue

        # Parse bin.
        tmp_cmd = "python ../lib/mavlogdump.py --planner --format csv --types PARM "+str(file)+" > "+filebuf
        subprocess.call(tmp_cmd, shell=True)

        # Read csv and remove file buffer.
        df = pd.read_csv(filebuf, sep=";")
        os.remove(filebuf)

        boot = df[df["Name"] == "STAT_BOOTCNT"].iloc[0]["Value"]
        flight = df[df["Name"] == "STAT_FLTTIME"].iloc[0]["Value"]
        runtime = df[df["Name"] == "STAT_RUNTIME"].iloc[0]["Value"]
        print(f"Boot: {int(boot)} times, Flight: {seconds_to_hoursminsec(flight)}, Runtime: {seconds_to_hoursminsec(runtime)}")

if __name__ == "__main__":
    opt = parse_option()
    main(opt)
