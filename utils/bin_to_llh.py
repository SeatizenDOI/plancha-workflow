import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime 


PATH_TO_BIN_FOLDER = Path("/media/bioeos/F/202404_plancha_session/20240412_REU-TESSIER_ASV-1_01/SENSORS")
header = "GPSDateStamp,GPSTimeStamp,GPSLatitude,GPSLongitude,elevation,fix,nbsat,sdn,sde,sdu,sdne,sdeu,sdun,age,ratio".split(',')

def main():
    if not Path.exists(PATH_TO_BIN_FOLDER):
        return

    for file in sorted(list(PATH_TO_BIN_FOLDER.iterdir())):
        if file.suffix != ".BIN": continue

        filebuf = Path('./tmp.csv')
         # Parse bin.
        tmp_cmd = "python ../lib/mavlogdump.py --planner --format csv --type GPS "+str(file)+" > "+str(filebuf)
        subprocess.call(tmp_cmd, shell=True)

        # Read csv and remove file buffer.
        d = pd.read_csv(filebuf, sep=";")
        filebuf.unlink()
        
        data = []
        for _, row in d.iterrows():
            dt_object = datetime.fromtimestamp(row["timestamp"])
            date = dt_object.strftime("%Y/%m/%d")
            time = dt_object.strftime("%H:%M:%S.f")
            data.append([date, time, row["Lat"], row["Lng"]])

        # Build dataframe
        df = pd.DataFrame(data, columns=header[0:4])
        for a in header[4:]:
            df[a] = 5 if a == "fix" else 0.0
        
        # Save llh.txt
        FILENAME_TXT = f"{file.name}_LLH.txt"
        df.to_csv(Path(PATH_TO_BIN_FOLDER, FILENAME_TXT), index=False)

        # Save llh.LLH
        FILENAME_LLH = FILENAME_TXT.replace(".txt", ".LLH")
        df.to_csv(Path(PATH_TO_BIN_FOLDER, FILENAME_LLH), index=False, sep=" ", header=False)

if __name__ == "__main__":
    main()