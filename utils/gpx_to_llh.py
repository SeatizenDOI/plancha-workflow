"""
    Convert GPX file to LLH file
"""

import pandas as pd
from pathlib import Path

FOLDER = Path("/media/bioeos/F/202305_plancha_session/20230430_MDG-NOSYVE_MASK-1_00/GPS/DEVICE")

header = "GPSDateStamp,GPSTimeStamp,GPSLatitude,GPSLongitude,elevation,fix,nbsat,sdn,sde,sdu,sdne,sdeu,sdun,age,ratio".split(',')
for file in FOLDER.iterdir():
    if file.suffix != ".gpx": continue

    data = []
    with open(file, "r") as file:
        lat, lon, date, time = None, None, None, None
        waitingTime = False
        for row in file:
            row = row.replace("\n", "")

            if not waitingTime and "<trkpt" in row:
                waitingTime = True
                lat = float(row.split(" ")[-2].replace('lat="', '').replace('"', ''))
                lon = float(row.split(" ")[-1].replace('lon="', '').replace('">', ''))
            elif waitingTime and "<time>" in row:
                waitingTime = False
                date = row.split("T")[0].split(">")[1].replace("-", "/")
                time = row.split("T")[1].split("Z")[0]
                data.append((date, time, lat, lon))
            

    # Build dataframe
    df = pd.DataFrame(data, columns=header[0:4])
    for a in header[4:]:
        df[a] = 5 if a == "fix" else 0.0
    
    # Save llh.txt
    date, time, _, _ = data[0]
    FILENAME_TXT = f"{date.replace('/', '')}{time.replace(':', '').split('.')[0]}.txt"
    df.to_csv(Path(FOLDER, FILENAME_TXT), index=False)

    # Save llh.LLH
    FILENAME_LLH = FILENAME_TXT.replace(".txt", ".LLH")
    df.to_csv(Path(FOLDER, FILENAME_LLH), index=False, sep=" ", header=False)
    






